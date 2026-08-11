#!/usr/bin/env python3
"""Bake Mhizha's chat behaviour into a GGUF's embedded chat template.

DEPENDENCY-FREE BY DESIGN. Python 3.8+ standard library only, no pip, no `gguf` package,
no numpy. This file lives at the repo root, not under scripts/, because the ADTC evaluator
runs `download_model.sh` in an environment we do not control and cannot install into. A
bake step that needed `pip install` would be a submission that fails on someone else's
machine, so the GGUF container format is parsed here by hand.

WHAT IT CHANGES
---------------
Exactly one metadata key: `tokenizer.chat_template`. Tensor data is copied byte for byte,
so the parameter count is untouched and the profiler's +/-15% fraud check is unaffected.

Two wrappers are prepended to the model's own template, which then runs unmodified:

1. thinking off, for templates that branch on `enable_thinking`.
   MEASURED: stock Qwen3.5-0.8B through llama-server returned EMPTY content on every turn,
   having spent its whole token budget inside an unclosed <think> block
   (finish_reason "length"). llama-server defines enable_thinking as true, overriding the
   model's own default, and the client-side override is a flag only the caller can send.
2. a default system message, applied only when the caller supplies none.

WHAT MAY NOT GO IN
------------------
The baked prompt carries POSTURE AND SAFETY BEHAVIOUR ONLY. Never an agronomic fact: no
planting date, no dosage, no rate, no product name, no threshold. CLAUDE.md rule 4 does not
relax because the text lives in model metadata rather than the corpus, and a baked fact
would be an invented fact delivered to a judge with no source.

Usage:
    python3 bake_template.py --in model.gguf --out baked.gguf
    python3 bake_template.py --in model.gguf --show
    python3 bake_template.py --in model.gguf --out baked.gguf --prompt-file competition/system_prompt.txt
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys

# ---------------------------------------------------------------- GGUF primitives

MAGIC = b"GGUF"
CHAT_TEMPLATE_KEY = "tokenizer.chat_template"
ALIGNMENT_KEY = "general.alignment"
DEFAULT_ALIGNMENT = 32

# GGUF metadata value types.
(T_UINT8, T_INT8, T_UINT16, T_INT16, T_UINT32, T_INT32, T_FLOAT32, T_BOOL,
 T_STRING, T_ARRAY, T_UINT64, T_INT64, T_FLOAT64) = range(13)

_FIXED = {
    T_UINT8: ("<B", 1), T_INT8: ("<b", 1),
    T_UINT16: ("<H", 2), T_INT16: ("<h", 2),
    T_UINT32: ("<I", 4), T_INT32: ("<i", 4),
    T_FLOAT32: ("<f", 4), T_BOOL: ("<?", 1),
    T_UINT64: ("<Q", 8), T_INT64: ("<q", 8), T_FLOAT64: ("<d", 8),
}


class GGUFError(RuntimeError):
    """The file is not a GGUF we can safely rewrite."""


class _Reader:
    def __init__(self, fh):
        self.fh = fh

    def read(self, n: int) -> bytes:
        data = self.fh.read(n)
        if len(data) != n:
            raise GGUFError(f"unexpected end of file wanting {n} bytes")
        return data

    def u32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.read(8))[0]

    def string(self) -> str:
        return self.read(self.u64()).decode("utf-8", "replace")

    def skip_value(self, vtype: int) -> None:
        """Advance past one value. Needed to find the key we care about."""
        if vtype in _FIXED:
            self.read(_FIXED[vtype][1])
        elif vtype == T_STRING:
            self.read(self.u64())
        elif vtype == T_ARRAY:
            item_type = self.u32()
            count = self.u64()
            if item_type in _FIXED:
                self.read(_FIXED[item_type][1] * count)
            elif item_type == T_STRING:
                for _ in range(count):
                    self.read(self.u64())
            else:
                raise GGUFError(f"unsupported array item type {item_type}")
        else:
            raise GGUFError(f"unsupported metadata value type {vtype}")


def _write_string(out, text: str) -> None:
    raw = text.encode("utf-8")
    out.write(struct.pack("<Q", len(raw)))
    out.write(raw)


def _align_up(offset: int, alignment: int) -> int:
    remainder = offset % alignment
    return offset if remainder == 0 else offset + (alignment - remainder)


def _scan(path: str):
    """Return (kv_entries, kv_section_end, tensor_info_end, alignment, tensor_count).

    kv_entries is a list of (key, raw_bytes_of_the_whole_entry). Keeping each entry as
    raw bytes means every value type round-trips exactly, including ones this script
    does not otherwise understand.
    """
    with open(path, "rb") as fh:
        reader = _Reader(fh)
        if reader.read(4) != MAGIC:
            raise GGUFError(f"{path} is not a GGUF file (bad magic)")
        version = reader.u32()
        if version != 3:
            raise GGUFError(
                f"{path} is GGUF v{version}; this script is written against v3. "
                "Refusing to guess at a different layout."
            )
        tensor_count = reader.u64()
        kv_count = reader.u64()

        entries = []
        alignment = DEFAULT_ALIGNMENT
        for _ in range(kv_count):
            start = fh.tell()
            key = reader.string()
            vtype = reader.u32()
            value_start = fh.tell()
            reader.skip_value(vtype)
            end = fh.tell()
            fh.seek(start)
            raw = fh.read(end - start)
            entries.append((key, raw))
            if key == ALIGNMENT_KEY and vtype in (T_UINT32, T_UINT64):
                alignment = struct.unpack(
                    _FIXED[vtype][0], raw[value_start - start:value_start - start + _FIXED[vtype][1]]
                )[0]
        kv_end = fh.tell()

        # Tensor info: name, n_dims, dims[n_dims], type, offset
        for _ in range(tensor_count):
            reader.string()
            n_dims = reader.u32()
            reader.read(8 * n_dims)
            reader.u32()
            reader.u64()
        tensor_info_end = fh.tell()

    if alignment <= 0 or (alignment & (alignment - 1)) != 0:
        raise GGUFError(f"implausible alignment {alignment}")
    return entries, kv_end, tensor_info_end, alignment, tensor_count


def read_template(path: str):
    entries, *_ = _scan(path)
    for key, raw in entries:
        if key != CHAT_TEMPLATE_KEY:
            continue
        # entry = keylen(8) + key + vtype(4) + strlen(8) + str
        offset = 8 + len(key.encode("utf-8"))
        vtype = struct.unpack("<I", raw[offset:offset + 4])[0]
        if vtype != T_STRING:
            raise GGUFError(f"{CHAT_TEMPLATE_KEY} is type {vtype}, expected string")
        offset += 4
        length = struct.unpack("<Q", raw[offset:offset + 8])[0]
        offset += 8
        return raw[offset:offset + length].decode("utf-8", "replace")
    return None


def region_digests(path: str):
    """sha256 of the tensor-info block and of the tensor data region.

    These are the parts a template edit must never touch. The data region is located
    from the file's own alignment rather than assumed, so a file whose metadata section
    changed length is still compared at the right offset.
    """
    _, kv_end, tensor_info_end, alignment, _ = _scan(path)
    data_start = _align_up(tensor_info_end, alignment)

    info = hashlib.sha256()
    data = hashlib.sha256()
    with open(path, "rb") as fh:
        fh.seek(kv_end)
        info.update(fh.read(tensor_info_end - kv_end))
        fh.seek(data_start)
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            data.update(chunk)
    return info.hexdigest(), data.hexdigest()


def assert_tensors_untouched(src: str, dst: str) -> None:
    """Fail loudly if a bake altered anything but metadata.

    A corrupted tensor region would not necessarily crash llama.cpp; it could produce a
    model that loads and generates subtly wrong output, which is far worse than a clean
    failure and would be nearly impossible to attribute later.
    """
    src_info, src_data = region_digests(src)
    dst_info, dst_data = region_digests(dst)
    if src_info != dst_info:
        raise GGUFError(
            f"tensor-info block changed during bake ({src_info[:16]} -> {dst_info[:16]}). "
            "Tensor offsets may no longer be valid. Refusing to keep the output."
        )
    if src_data != dst_data:
        raise GGUFError(
            f"tensor DATA changed during bake ({src_data[:16]} -> {dst_data[:16]}). "
            "The weights are not the ones we downloaded. Refusing to keep the output."
        )


def roundtrip_is_byte_identical(src: str, tmp_path: str) -> bool:
    """No-op invariant: rewriting with the UNCHANGED template must reproduce the file.

    If this fails, the rewriter is lossy somewhere (a metadata type it does not
    round-trip, or padding it recomputes differently), and any real bake is suspect even
    when it happens to load.
    """
    current = read_template(src)
    if current is None:
        raise GGUFError(f"{src} has no {CHAT_TEMPLATE_KEY} to round-trip")
    rewrite(src, tmp_path, current)
    with open(src, "rb") as a, open(tmp_path, "rb") as b:
        while True:
            ca, cb = a.read(8 * 1024 * 1024), b.read(8 * 1024 * 1024)
            if ca != cb:
                return False
            if not ca:
                return True


def rewrite(src: str, dst: str, new_template: str) -> None:
    """Copy the GGUF, replacing only tokenizer.chat_template.

    Tensor info is copied verbatim and the data section is re-aligned to the same
    boundary, so the tensor offsets (which are relative to the start of the data section)
    stay correct even though the metadata section changed length.
    """
    entries, kv_end, tensor_info_end, alignment, tensor_count = _scan(src)
    if not any(key == CHAT_TEMPLATE_KEY for key, _ in entries):
        raise GGUFError(
            f"{src} has no {CHAT_TEMPLATE_KEY}. Without one there is no channel to bake "
            "into, and llama-server would fall back to a built-in format."
        )

    data_start = _align_up(tensor_info_end, alignment)

    tmp = dst + ".partial"
    with open(src, "rb") as fin, open(tmp, "wb") as out:
        out.write(MAGIC)
        out.write(struct.pack("<I", 3))
        out.write(struct.pack("<Q", tensor_count))
        out.write(struct.pack("<Q", len(entries)))

        for key, raw in entries:
            if key == CHAT_TEMPLATE_KEY:
                _write_string(out, key)
                out.write(struct.pack("<I", T_STRING))
                _write_string(out, new_template)
            else:
                out.write(raw)

        fin.seek(kv_end)
        out.write(fin.read(tensor_info_end - kv_end))

        padding = _align_up(out.tell(), alignment) - out.tell()
        out.write(b"\0" * padding)

        fin.seek(data_start)
        while True:
            chunk = fin.read(8 * 1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

    os.replace(tmp, dst)


# ---------------------------------------------------------------- the wrappers

THINKING_GUARD = "{%- set enable_thinking = false -%}"


def template_uses_thinking(template: str) -> bool:
    return "enable_thinking" in template


def inject_thinking_off(template: str) -> str:
    """Force the no-thinking branch whatever the server passes in."""
    return THINKING_GUARD + template


def jinja_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def inject_default_system(template: str, prompt: str) -> str:
    """Prepend a default system message, only when the caller supplied none.

    The model's own template is left untouched and still does all turn formatting: every
    family formats differently and rewriting that would silently corrupt every response.
    A caller-supplied system message always wins, because this sets a default rather than
    overriding a user.
    """
    guard = (
        "{%- if messages and messages[0]['role'] == 'system' -%}"
        "{%- set messages = messages -%}"
        "{%- else -%}"
        "{%- set messages = [{'role': 'system', 'content': '"
        + jinja_escape(prompt)
        + "'}] + messages -%}"
        "{%- endif -%}"
    )
    return guard + template


def _cleanup(*paths: str) -> None:
    """Never leave a suspect artifact on disk: a later step might pick it up."""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


DEFAULT_PROMPT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "competition", "system_prompt.txt"
)


def load_prompt(path: str) -> str:
    if not os.path.exists(path):
        raise SystemExit(f"missing system prompt file: {path}")
    with open(path, encoding="utf-8") as fh:
        text = fh.read().strip()
    if not text:
        raise SystemExit(f"{path} is empty")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="Bake chat behaviour into a GGUF template.")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst")
    ap.add_argument("--show", action="store_true", help="print the template and exit")
    ap.add_argument("--prompt-file", default=DEFAULT_PROMPT_FILE)
    ap.add_argument("--keep-thinking", action="store_true",
                    help="do not force reasoning off (default is to force it off)")
    ap.add_argument("--no-persona", action="store_true",
                    help="thinking guard only, no system prompt. This is the 'minimal "
                         "bake' arm: it isolates the thinking fix from the persona so "
                         "persona lift can be read on its own.")
    args = ap.parse_args()

    if not os.path.exists(args.src):
        print(f"error: {args.src} not found", file=sys.stderr)
        return 2

    try:
        current = read_template(args.src)
    except GGUFError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.show:
        print(current if current is not None else "(no tokenizer.chat_template)")
        return 0

    if not args.dst:
        print("error: --out is required unless --show", file=sys.stderr)
        return 2
    if current is None:
        print(f"error: {args.src} has no {CHAT_TEMPLATE_KEY}", file=sys.stderr)
        return 1

    new_template = current
    prompt = None
    if not args.no_persona:
        prompt = load_prompt(args.prompt_file)
        new_template = inject_default_system(new_template, prompt)

    thinking = template_uses_thinking(current)
    if thinking and not args.keep_thinking:
        new_template = inject_thinking_off(new_template)

    print(f"source:   {args.src} ({os.path.getsize(args.src) / 1048576:.0f} MB)")
    print(f"persona:  {'OMITTED (--no-persona)' if args.no_persona else args.prompt_file}")
    if thinking:
        print(f"thinking: branches on enable_thinking; reasoning "
              f"{'kept ON' if args.keep_thinking else 'FORCED OFF'}")
    else:
        print("thinking: template does not branch on enable_thinking; no guard needed")
    print(f"template: {len(current)} -> {len(new_template)} chars")

    try:
        rewrite(args.src, args.dst, new_template)
    except GGUFError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Guard 1: no-op round-trip. If rewriting with the unchanged template does not
    # reproduce the source byte for byte, the rewriter is lossy and no bake is trustworthy.
    noop_path = args.dst + ".noop"
    try:
        identical = roundtrip_is_byte_identical(args.src, noop_path)
    except GGUFError as exc:
        print(f"error: round-trip check failed: {exc}", file=sys.stderr)
        _cleanup(noop_path, args.dst)
        return 1
    finally:
        _cleanup(noop_path)
    if not identical:
        print(
            "error: no-op round-trip is NOT byte-identical. The rewriter is lossy on "
            "this file, so the baked output cannot be trusted even if it loads.",
            file=sys.stderr,
        )
        _cleanup(args.dst)
        return 1
    print("round-trip: no-op rewrite is byte-identical")

    # Guard 2: the bake changed metadata and nothing else.
    try:
        assert_tensors_untouched(args.src, args.dst)
    except GGUFError as exc:
        print(f"error: {exc}", file=sys.stderr)
        _cleanup(args.dst)
        return 1
    print("tensors:  tensor-info and data regions hash-identical to source")

    verify = read_template(args.dst)
    if verify != new_template:
        print("error: the template did not survive the rewrite", file=sys.stderr)
        _cleanup(args.dst)
        return 1
    if prompt and prompt.splitlines()[0][:40] not in verify:
        print("error: the system prompt is missing from the written template",
              file=sys.stderr)
        return 1

    print(f"done: {args.dst} ({os.path.getsize(args.dst) / 1048576:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
