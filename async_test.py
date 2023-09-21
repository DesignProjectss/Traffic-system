import uasyncio as asyncio
async def foo(n):
    for x in range(10 + n):
        print(f"Task {n} running.")
        await asyncio.sleep(1 + n/10)
    print(f"Task {n} done")

async def main():
    async with asyncio.TaskGroup() as tg:  # Context manager pauses until members terminate
        for n in range(4):
            tg.create_task(foo(n))  # tg.create_task() creates a member task
    print("TaskGroup done")  # All tasks have terminated

asyncio.run(main())
