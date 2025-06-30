# letterboxd bot (name pending)

features

- follow letterboxd users to get notified when they add a film to their diary
- use /whoknows to see who's watched/rated films

## dev setup

### requirements

- mise
- a postgres db somewhere

### setup

create `.env` and fill out
```
DISCORD_TOKEN=[discord bot token]
DATABASE_URL=postgresql://...
optional: TEST_GUILD_ID=[guild id, allows for realtime slash command updates. use if they're not updating]
```

### running

`mise run dev`
