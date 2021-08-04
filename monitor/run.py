from monitor.movie_trailer import run_movie_trailer
from monitor.resiliosync import run_resilosync


def run_monitor():
    run_movie_trailer()
    run_resilosync()


if __name__ == "__main__":
    run_monitor()
