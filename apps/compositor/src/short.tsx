import React from 'react';
import {AbsoluteFill, Audio, Video, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import captions from './captions.json';

type Cue = {start:number;end:number;text:string;beat_id:string};
const cues: Cue[] = captions;

export const Short: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sec = frame / fps;
  const current = cues.find((cue) => sec >= cue.start && sec < cue.end);
  return (
    <AbsoluteFill style={{backgroundColor:'#80adc7'}}>
      <AbsoluteFill>
        <Video src={staticFile('visuals.mp4')} muted />
      </AbsoluteFill>
      <Audio src={staticFile('narration.wav')} />
      {current && (
        <div style={{
          position:'absolute',left:55,right:55,bottom:215,
          fontFamily:'Arial, sans-serif',fontWeight:900,
          fontSize:57,lineHeight:1.12,textAlign:'center',
          textTransform:'uppercase',color:'#ffffff',
          WebkitTextStroke:'4px #101820',
          textShadow:'0 4px 2px rgba(0,0,0,.7)',
          overflowWrap:'break-word',
        }}>{current.text}</div>
      )}
    </AbsoluteFill>
  );
};
