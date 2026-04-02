from sqlalchemy import Column, String, Integer, Date, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class Mood(Base):
    __tablename__ = "moods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    mood_level = Column(Integer, nullable=False)  # 1-5 range
    emoji = Column(String(16), nullable=True)
    emotion = Column(String(50), nullable=True)
    tags = Column(Text, nullable=True)  # comma-separated tags
    notes = Column(Text, nullable=True)  # optional journal entry

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='unique_user_date'),
        Index('idx_user_date', 'user_id', 'date'),
    )

    # Relationship
    user = relationship("User", back_populates="moods")

    def __repr__(self):
        return (
            f"<Mood(id={self.id}, user_id={self.user_id}, date={self.date}, "
            f"mood_level={self.mood_level}, emoji={self.emoji}, emotion={self.emotion})>"
        )