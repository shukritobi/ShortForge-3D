import React from 'react';
import {Composition} from 'remotion';
import {Short} from './short';

export const Root: React.FC = () => (
  <Composition
    id="ShortForgeShort"
    component={Short}
    durationInFrames={960}
    fps={24}
    width={720}
    height={1280}
  />
);
