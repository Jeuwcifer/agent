---
name: sync-skills
description: Uploads and synchronizes all pi agent skills to the remote GitHub repository. Triggers on requests like "sync skills", "upload my skills to github", "backup skills", or "push skills".
---

# Sync Skills

This skill automates the process of copying all local pi agent skills from the `.agents/skills` and `.pi/agent/skills` directories and pushing them to the remote GitHub repository located at `~/Repos/agent`.

## Workflow
1. Run the provided script `sync.sh` located in the skill directory (`/home/user/.agents/skills/sync-skills/sync.sh`).
2. The script will automatically:
   - Copy all skill folders into the `~/Repos/agent` directory.
   - Stage and commit the changes with an auto-generated timestamp.
   - Push the changes to GitHub using the cached/configured credentials.
3. Once the script finishes successfully, report back to the user that the synchronization is complete.

## Execution
To perform the upload, execute the following command:
```bash
bash /home/user/.agents/skills/sync-skills/sync.sh
```
