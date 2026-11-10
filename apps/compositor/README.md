# Optional Remotion caption compositor

The default production path uses FFmpeg and local ASS subtitle burning, so
there is no Node/Remotion dependency to produce a full MP4.

To use animated React captions instead:

1. First generate Blender frames, Piper narration, and caption data.
2. Export the frames to a silent MP4 with FFmpeg:
   ffmpeg -y -framerate 24 -start_number 1 -i output/water_tower/frames/frame_%06d.png -c:v libx264 -pix_fmt yuv420p -t 40 apps/compositor/public/visuals.mp4
3. Copy output/water_tower/audio/narration.wav to apps/compositor/public/narration.wav
4. Copy output/water_tower/captions/captions.json to apps/compositor/src/captions.json
5. From apps/compositor, run npm install && npm run typecheck && npm run render

Remotion reads the same validated captions JSON and uses the same 40-second
scene duration. This optional mode is designed for later visual customization.
Review Remotion licensing for your organization size before commercial use.
