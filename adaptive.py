from config import VIDEO_QUALITIES


class AdaptiveController:
    def __init__(self):
        self.level = 0

    def degrade(self):
        if self.level < len(VIDEO_QUALITIES) - 1:
            self.level += 1

    def upgrade(self):
        if self.level > 0:
            self.level -= 1

    def current(self):
        return VIDEO_QUALITIES[self.level]
