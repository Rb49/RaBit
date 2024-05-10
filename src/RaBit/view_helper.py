import time


def raise_error(loading_window, msg: str):
    """
    raises an error to the loading screen
    """
    if loading_window is None:
        return
    loading_window.frame.description2.configure(text=msg)
    loading_window.frame.description2.configure(text_color="red")
    loading_window.frame.progressbar.destroy()
    time.sleep(1000000)
