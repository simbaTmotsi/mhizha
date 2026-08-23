import React from 'react';
import {Composition} from 'remotion';
import {Mhizha, TOTAL} from './Mhizha';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Mhizha"
    component={Mhizha}
    durationInFrames={Math.round(TOTAL * 30)}
    fps={30}
    width={1920}
    height={1080}
  />
);
