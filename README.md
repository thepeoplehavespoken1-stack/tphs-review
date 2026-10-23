# TPHS review videos

## Where things go
- **Google Drive first:** Final Run Videos TPHS → "This Is [State]" folder → `This_Is_[State]_FULL.mp4`
  https://drive.google.com/drive/folders/1dD84qulCf_LqLY-DSbz2Sj9oJUt0Hs9e
- **GitHub Releases:** one release per video
  - Original: tag `[state]-full`, title `[State] FULL`
  - Fixed by the editor: tag `[state]-fixed`, title `[State] FIXED`
  - Virginia's first upload is tag `v1`

## Copy new videos from Drive (automatic)
1. Add a line to `videos.txt`: `DRIVE_FILE_ID This_Is_[State]_FULL.mp4`
2. Actions → "Copy FULL videos from Drive to Releases" → Run workflow
3. Drive files must be "Anyone with the link → Viewer" while copying. It skips videos already copied.
