"""Korean/English UI strings.

Runtime texts are selected per interaction via :func:`t` using the user's
client locale (``interaction.locale``). Command names/descriptions are
localized at sync time by :class:`KoreanTranslator`, which looks up the same
table - so every ``locale_str``-wrapped English string must have a key here.
Command *names* are intentionally not localized (the ``bamboo`` brand stays).
"""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

KO: dict[str, str] = {
    # -- generic -----------------------------------------------------------
    "Something went wrong.": "문제가 발생했어요. 잠시 후 다시 시도해 주세요.",
    "Only moderators can use this.": "이 기능은 운영자만 사용할 수 있어요.",
    "Moderation panel closed.": "관리 패널을 닫았어요.",
    "This command only works in a server channel.": "이 명령어는 서버 채널에서만 사용할 수 있어요.",
    "I need the **Send Messages** and **Attach Files** permissions in this channel.":
        "이 채널에서 **메시지 보내기** 및 **파일 첨부** 권한이 필요해요.",
    # -- /bamboo gating ----------------------------------------------------
    "You are blocked from sending anonymous messages in this server.":
        "이 서버에서 익명 메시지 전송이 차단되었어요.",
    "You are sending anonymous messages too fast - try again {retry}.":
        "익명 메시지를 너무 빠르게 보내고 있어요 - {retry}에 다시 시도해 주세요.",
    # -- compose modal -----------------------------------------------------
    "Anonymous message": "익명 메시지",
    "Message": "메시지",
    "What should be sent?": "무엇을 보낼까요?",
    "Media (optional)": "미디어 (선택)",
    "Photos, a video, or audio. Up to {n} files.": "사진, 동영상 또는 오디오. 최대 {n}개 파일.",
    "Write some text or attach at least one file.":
        "텍스트를 입력하거나 파일을 하나 이상 첨부해 주세요.",
    "Every attachment was over the 10 MiB bot upload limit, so there is nothing to send.":
        "모든 첨부 파일이 봇 업로드 제한(10MiB)을 초과해서 보낼 내용이 없어요.",
    "Could not send the message: {exc}": "메시지를 보낼 수 없어요: {exc}",
    "Sent anonymously: {url}": "익명으로 보냈어요: {url}",
    "-# {n} attachment(s) skipped (over the 10 MiB bot upload limit).":
        "-# 첨부 파일 {n}개가 봇 업로드 제한(10MiB)을 초과해서 제외되었어요.",
    # -- buttons on published messages -------------------------------------
    "See OP": "작성자 보기",
    "Moderation": "관리",
    "Timeout": "타임아웃",
    "Block permanently": "영구 차단",
    "Cancel": "취소",
    # -- See OP ------------------------------------------------------------
    "I don't know who sent this - the identity may have been purged or the record is missing.":
        "이 메시지의 작성자를 알 수 없어요 - 보존 기간이 지나 삭제되었거나 기록이 없어요.",
    "Anonymous message - original poster": "익명 메시지 - 작성자",
    "User": "사용자",
    "Username": "사용자명",
    "User ID": "사용자 ID",
    "Posted": "게시 시각",
    "unknown (account may be deleted)": "알 수 없음 (계정이 삭제되었을 수 있어요)",
    # -- moderation panel --------------------------------------------------
    "Moderation for {user}": "{user} 관리",
    "That user is no longer in this server - use **Block permanently** instead.":
        "그 사용자는 더 이상 서버에 없어요 - 대신 **영구 차단**을 사용해 주세요.",
    "I need the **Moderate Members** permission to time people out.":
        "타임아웃을 적용하려면 **멤버 제한 시간 설정** 권한이 필요해요.",
    # -- timeout modal -----------------------------------------------------
    "Timeout member": "멤버 타임아웃",
    "Duration": "기간",
    "1 hour": "1시간",
    "6 hours": "6시간",
    "1 day": "1일",
    "3 days": "3일",
    "7 days": "7일",
    "28 days": "28일",
    "Reason (optional)": "사유 (선택)",
    "I could not time that member out (missing permissions or role hierarchy).":
        "타임아웃을 적용할 수 없어요 (권한 부족 또는 역할 계층 문제).",
    "Timeout failed: {exc}": "타임아웃 실패: {exc}",
    "Timed out {member} until {until}.": "{member}님을 {until}까지 타임아웃했어요.",
    "Timeout ({hours}h)": "타임아웃 ({hours}시간)",
    "Timeout ({seconds}s)": "타임아웃 ({seconds}초)",
    # -- block modal -------------------------------------------------------
    "Block from anonymous messages": "익명 메시지 차단",
    "Blocked {user} from using anonymous messages in this server. `/bamboo-mod unblock` reverts it.":
        "이 서버에서 {user}님의 익명 메시지 사용을 차단했어요. `/bamboo-mod unblock`으로 되돌릴 수 있어요.",
    "Permanent block": "영구 차단",
    # -- /bamboo-setup -----------------------------------------------------
    "Mod role cleared - anyone with **Manage Messages** can moderate.":
        "운영 역할이 초기화되었어요 - 이제 **메시지 관리** 권한이 있는 사람이면 누구나 운영할 수 있어요.",
    "Mod role set to {role}. Members holding it can use **See OP** / **Moderation**.":
        "운영 역할이 {role}(으)로 설정되었어요. 이 역할을 가진 멤버는 **작성자 보기** / **관리** 버튼을 사용할 수 있어요.",
    "Mod-log disabled.": "운영 로그가 비활성화되었어요.",
    "Mod-log set to {channel}.": "운영 로그 채널이 {channel}(으)로 설정되었어요.",
    "Cooldown disabled.": "쿨다운이 비활성화되었어요.",
    "Cooldown set to {seconds}s per user.": "사용자당 쿨다운이 {seconds}초로 설정되었어요.",
    "Anon bot configuration": "익명 메시지 봇 설정",
    "Mod role": "운영 역할",
    "Mod log": "운영 로그",
    "Cooldown": "쿨다운",
    "*not set*": "*설정 안 됨*",
    "*disabled*": "*비활성화*",
    "{seconds}s": "{seconds}초",
    # -- /bamboo-mod -------------------------------------------------------
    "You cannot block yourself.": "자기 자신은 차단할 수 없어요.",
    "You cannot block bots.": "봇은 차단할 수 없어요.",
    "Blocked {user} from anonymous messages. `/bamboo-mod unblock` reverts it.":
        "{user}님의 익명 메시지 사용을 차단했어요. `/bamboo-mod unblock`으로 되돌릴 수 있어요.",
    "Unblocked {user}.": "{user}님의 차단을 해제했어요.",
    "{user} was not blocked.": "{user}님은 차단되어 있지 않아요.",
    "No users are blocked.": "차단된 사용자가 없어요.",
    "Blocked users ({n})": "차단된 사용자 ({n}명)",
    "…and {n} more.": "…외 {n}명 더",
    # -- mod log -----------------------------------------------------------
    "Anon moderation - {action}": "익명 메시지 관리 - {action}",
    "Moderator": "운영자",
    "Target": "대상",
    "Reason": "사유",
    # -- command metadata (translator) --------------------------------------
    "Send an anonymous message to this channel": "이 채널에 익명 메시지를 보내요",
    "Configure the anonymous message system": "익명 메시지 시스템을 설정해요",
    "Moderate anonymous message users": "익명 메시지 사용자를 관리해요",
    "Set the moderator role for See OP / Moderation buttons":
        "작성자 보기 / 관리 버튼을 사용할 운영 역할을 설정해요",
    "Set the channel for moderation audit logs": "운영 감사 로그 채널을 설정해요",
    "Seconds between anonymous messages per user (0 disables)":
        "사용자당 익명 메시지 전송 간격(초, 0이면 비활성화)",
    "Show the current configuration": "현재 설정을 보여줘요",
    "Permanently block a user from anonymous messages": "사용자의 익명 메시지 사용을 영구 차단해요",
    "Lift an anonymous-message block": "익명 메시지 차단을 해제해요",
    "List users blocked from anonymous messages": "익명 메시지가 차단된 사용자 목록을 보여줘요",
    "Role that can use the See OP / Moderation buttons": "작성자 보기 / 관리 버튼을 사용할 수 있는 역할",
    "Channel for the moderation audit log": "운영 감사 로그를 기록할 채널",
    "Wait time in seconds per user (0 disables)": "사용자당 대기 시간(초, 0이면 비활성화)",
    "User to block": "차단할 사용자",
    "Reason for the block": "차단 사유",
    "User to unblock": "차단 해제할 사용자",
}


def is_korean(locale: Optional[discord.Locale]) -> bool:
    return locale == discord.Locale.korean


def t(locale: Optional[discord.Locale], template: str, /, **kwargs) -> str:
    """Translate ``template`` for ``locale`` and format it with ``kwargs``.

    Unknown templates fall back to their English source, so the English text
    doubles as the key.
    """
    if is_korean(locale):
        template = KO.get(template, template)
    return template.format(**kwargs) if kwargs else template


class KoreanTranslator(app_commands.Translator):
    """Localizes command names/descriptions marked with ``locale_str``."""

    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContextTypes,
    ) -> Optional[str]:
        if not is_korean(locale):
            return None
        return KO.get(str(string))
