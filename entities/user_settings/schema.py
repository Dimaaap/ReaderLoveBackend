from pydantic import BaseModel, ConfigDict


class UserSettingsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str

    email_notifications: bool
    reading_reminders: bool
    book_recommendations: bool
    is_public_profile: bool
    is_show_reading_progress: bool
    allow_friends_recommendations: bool
    show_statistics: bool
    show_bookshelf: bool
    show_favorite_books: bool
    show_notes: bool
    show_quotes: bool
    show_current_book: bool
    show_followers: bool
    allow_private_messages: bool
    show_online_status: bool
    show_last_seen: bool


class UserSettingsUpdateSchema(BaseModel):
    email_notifications: bool = True
    reading_reminders: bool = True
    book_recommendations: bool = True
    is_public_profile: bool = True
    is_show_reading_progress: bool = True
    allow_friends_recommendations: bool = True
    show_statistics: bool = True
    show_bookshelf: bool = True
    show_favorite_books: bool = True
    show_notes: bool = True
    show_quotes: bool = True
    show_current_book: bool = True
    show_followers: bool = True
    allow_private_messages: bool = True
    show_online_status: bool = True
    show_last_seen: bool = True
