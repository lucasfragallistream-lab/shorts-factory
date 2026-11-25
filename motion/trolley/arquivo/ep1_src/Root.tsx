import React from 'react';
import {Composition} from 'remotion';
import {Video} from './Video';
export const Root: React.FC = () => (<>
  <Composition id="Video" component={Video} durationInFrames={1830} fps={30} width={1080} height={1920} />
  <Composition id="Preview" component={Video} durationInFrames={1830} fps={30} width={540} height={960} />
</>);
