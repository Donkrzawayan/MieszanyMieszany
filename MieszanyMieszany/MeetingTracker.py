from datetime import UTC, datetime


class MeetingTracker:
    def __init__(self):
        self.meetings = {}

    def _end_meeting(self, channel):
        start_time = self.meetings.pop(channel.id, None)
        if start_time:
            return datetime.now(UTC) - start_time

    def _start_meeting(self, channel):
        self.meetings[channel.id] = datetime.now(UTC)

    def update_voice_state(self, member, before, after):
        if before.channel == after.channel:
            return

        if before.channel and len(before.channel.members) < 2:
            if before.channel.id in self.meetings and self.meetings[before.channel.id]:
                return self._end_meeting(before.channel)

        if after.channel and len(after.channel.members) >= 2:
            if after.channel.id not in self.meetings or not self.meetings[after.channel.id]:
                return self._start_meeting(after.channel)

    def cuttent_meeting(self, channel):
        if self.meetings[channel.id] and len(channel.members) >= 2:
            start_time = self.meetings[channel.id]
            return datetime.now(UTC) - start_time
