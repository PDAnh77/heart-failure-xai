from core.storage import storage


class SupabaseClientWrapper:
    """Wrapper tương thích ngược để hỗ trợ cả Supabase Storage lẫn Local File Storage."""

    def __init__(self):
        self.storage = storage


supabase = SupabaseClientWrapper()
