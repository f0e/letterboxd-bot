import datetime

from letterboxdpy import user as lb_user  # type: ignore


def get_diary(user: lb_user.User, last_diary_entry: datetime.date | None = None):
    lb_diary_to_process: list[dict] = []

    page = 1
    while True:
        lb_page_diary_entries: dict[str, dict] = user.get_diary(page=page)["entries"]
        if not lb_page_diary_entries:
            # reached the end.
            return lb_diary_to_process

        for entry_key, entry in lb_page_diary_entries.items():
            # convert date dict to date object
            entry["date"] = datetime.date(
                entry["date"]["year"],
                entry["date"]["month"],
                entry["date"]["day"],
            )

            if last_diary_entry:
                if entry["date"] <= last_diary_entry:
                    # reached stuff we've already processed
                    return lb_diary_to_process

            lb_diary_to_process.append(entry)

            if not last_diary_entry:
                # just getting the newest :)
                return lb_diary_to_process

        page += 1
