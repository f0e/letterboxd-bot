from letterboxdpy import user as lb_user  # type: ignore
from sqlalchemy.orm import Session

from ..database import MovieWatch


def update_user_films(db: Session, username: str):
    user = lb_user.User(username=username)

    user_films = user.get_films()  # todo: modify fn to return more info - date, review url. may need to use different function?

    # todo: this can def be optimised
    for movie_slug, watch in user_films["movies"].items():
        movie_id = watch["id"]

        # Check if this watch already exists
        existing_watch = (
            db.query(MovieWatch)
            .filter_by(movie_id=movie_id, letterboxd_username=username)
            .first()
        )

        rating = watch.get("rating")
        liked = watch.get("liked")

        if existing_watch:
            if existing_watch.rating != rating:
                existing_watch.rating = rating

            if existing_watch.liked != liked:
                existing_watch.liked = liked
        else:
            new_watch = MovieWatch(
                movie_id=movie_id,
                letterboxd_username=username,
                rating=rating,
                liked=liked,
            )
            db.add(new_watch)

    db.commit()
