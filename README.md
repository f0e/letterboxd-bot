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
optional: BOT_OWNER_ID=[owner id, enables permissions for /sync to sync slash commands manually]
optional: BOT_HOME_GUILD_ID=[home server id, always syncs /sync command]
```

and run `mise run setup`

### running

`mise run dev`
