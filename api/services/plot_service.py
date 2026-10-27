import io
import uuid
import matplotlib.pyplot as plt
from core.supabase_client import supabase


def upload_plot(figure, folder_path, bucket_name="heart-prediction-xai-reports"):
    """
    Utility function to save a matplotlib figure and upload to Supabase.
    """
    buf = io.BytesIO()
    figure.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)

    unique_filename = f"{uuid.uuid4()}.png"
    storage_path = f"{folder_path}/{unique_filename}"

    try:
        supabase.storage.from_(bucket_name).upload(
            path=storage_path, file=buf.getvalue(), file_options={"content-type": "image/png"}
        )
        return supabase.storage.from_(bucket_name).get_public_url(storage_path)
    except Exception as e:
        print(f"Upload Error: {str(e)}")
        return None
    finally:
        plt.close(figure)
