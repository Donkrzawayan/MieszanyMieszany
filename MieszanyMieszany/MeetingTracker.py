from datetime import UTC, datetime, timedelta


class MeetingTracker:
    def __init__(self):
        self.meetings = {}

    def _end_meeting(self, channel):
        meeting_info = self.meetings.get(channel.id)
        if meeting_info:
            end_time = datetime.now(UTC)
            duration = end_time - meeting_info['start_time']
            meeting_info['duration'] += duration  # Accumulate duration in case of multiple meetings
            meeting_info['is_meeting'] = False
            print(f"Meeting ended in channel {channel.name}. Duration: {meeting_info['duration']}")
            return meeting_info['duration']

    def _start_meeting(self, channel):
        self.meetings[channel.id] = {
            'start_time': datetime.now(UTC),
            'is_meeting': True,
            'duration': timedelta(0)
        }
        print(f"Meeting started in channel {channel.name} at {self.meetings[channel.id]['start_time']}")

    def update_voice_state(self, member, before, after):
        if before.channel == after.channel:
            return

        if before.channel and len(before.channel.members) < 2:
            if before.channel.id in self.meetings and self.meetings[before.channel.id]['is_meeting']:
                return self._end_meeting(before.channel)

        if after.channel and len(after.channel.members) >= 2:
            if after.channel.id not in self.meetings or not self.meetings[after.channel.id]['is_meeting']:
                return self._start_meeting(after.channel)