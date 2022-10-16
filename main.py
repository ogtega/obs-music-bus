#!venv/bin/python
import asyncio

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import MessageType
from dbus_next.message import Message
from dbus_next.signature import Variant

bus: MessageBus


async def out(data: dict[str, Variant]):
    artists: list[str] = data.get("xesam:artist", Variant("as", [])).value
    title: str = data.get("xesam:title", Variant("s", "")).value

    print(artists, title)


async def getProperty(name: str, prop: str):
    msg = await bus.call(
        Message(
            name,
            "/org/mpris/MediaPlayer2",
            "org.freedesktop.DBus.Properties",
            member="Get",
            signature="ss",
            body=["org.mpris.MediaPlayer2.Player", prop],
        )
    )

    assert msg and msg.message_type == MessageType.METHOD_RETURN
    return msg.body[0].value


async def signalCall():
    await bus.call(
        Message(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            member="AddMatch",
            signature="s",
            body=[
                (
                    "type='signal',"
                    "path='/org/mpris/MediaPlayer2',"
                    "member='PropertiesChanged',"
                    "interface='org.freedesktop.DBus.Properties'"
                )
            ],
        )
    )

    def handler(msg: Message):
        if (
            not msg._matches(
                message_type=MessageType.SIGNAL,
                interface="org.freedesktop.DBus.Properties",
                path="/org/mpris/MediaPlayer2",
                member="PropertiesChanged",
                signature="sa{sv}as",
            )
            or "Metadata" not in msg.body[1].keys()
        ):
            return

        metadata: dict[str, Variant] = msg.body[1].get("Metadata").value
        asyncio.get_running_loop().create_task(out(metadata))

    bus.add_message_handler(handler)


async def main():
    global bus

    bus = await MessageBus().connect()
    res = await bus.call(
        Message(
            destination="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="ListNames",
        )
    )

    assert res and res.message_type == MessageType.METHOD_RETURN

    names: list[str] = list(
        filter(lambda n: "org.mpris.MediaPlayer2" in n, res.body[0])
    )

    for name in names:
        status = await getProperty(name, "PlaybackStatus")

        if status == "Playing":
            await out(await getProperty(name, "Metadata"))

    await signalCall()

    await asyncio.Future()


asyncio.run(main())
