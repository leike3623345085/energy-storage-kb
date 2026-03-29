# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## 邮件发送规则

### Word附件正确发送方式
**问题**: 使用 `MIMEBase` 会导致QQ邮箱显示为BIN格式

**正确代码**:
```python
from email.mime.application import MIMEApplication

with open('file.docx', 'rb') as f:
    attachment = MIMEApplication(f.read())
    attachment.add_header('Content-Disposition', 'attachment', filename='file.docx')
    attachment.add_header('Content-Type', 
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    msg.attach(attachment)
```

**错误代码**（已废弃）:
```python
from email.mime.base import MIMEBase  # ❌ 不要用这个
attachment = MIMEBase('application', 'octet-stream')  # ❌ 会导致BIN格式
```

---

Add whatever helps you do your job. This is your cheat sheet.
