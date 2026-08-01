import asyncio, asyncpg
async def c():
    conn = await asyncpg.connect('postgresql://auditflow:auditflow@localhost:5432/auditflow')
    rows = await conn.fetch('SELECT source_id, COUNT(*) as cnt FROM embedding_items GROUP BY source_id ORDER BY cnt DESC')
    total = sum(r['cnt'] for r in rows)
    for r in rows:
        sid = r['source_id']
        cnt = r['cnt']
        print(f'  {sid:<35} {cnt}')
    print(f'  {"-"*45}')
    print(f'  TOTAL: {total} chunks')
    await conn.close()
asyncio.run(c())
