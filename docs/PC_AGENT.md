# ShortForge local PC diagnostics

This is an opt-in local tool, not remote control. It runs when you type a command,
does not poll GitHub, does not start a service, never opens network ports,
never uploads logs and never accepts shell commands from JSON.

From an activated PowerShell virtual environment:

    git pull
    python scripts/pc_agent.py doctor
    python scripts/pc_agent.py preview

To run in a portable/non-standard Blender installation:

    python scripts/pc_agent.py doctor --blender "D:\Apps\Blender\blender.exe"
    python scripts/pc_agent.py preview --blender "D:\Apps\Blender\blender.exe"

The runner checks Blender --version and performs a headless Python startup probe
before attempting the actual 480th-frame preview. It automatically searches PATH,
environment override SHORTFORGE_BLENDER, local config, normal Program Files
installation directories, Steam, and Blender's Windows App Paths registration.

You can invoke a reviewed JSON task (doctor, preview, tests, full only):

    python scripts/pc_agent.py job jobs/preview.json

A full video requires locally installed Blender, Piper, FFmpeg and voice:

    python scripts/pc_agent.py full --voice "C:\Voices\en_US-lessac-medium.onnx"

Each execution writes a folder inside output/diagnostics containing:
- doctor.json: versions, tool paths, headless probe, GPU, disk and requirements
- events.jsonl: job, process start and finish records
- stdout.log and stderr.log: Blender/Python output from the running process
- summary.json: status, hints, output path and tail of the logs

First share summary.json and doctor.json after reviewing them. Raw Blender logs
can contain Windows username, folder paths or other private information.
No file is sent anywhere automatically.

If Blender isn't installed, use the normal Blender 4.5 LTS installer or:

    winget install -e --id BlenderFoundation.Blender.LTS.4.5

Close/reopen PowerShell after installation and run doctor again.
