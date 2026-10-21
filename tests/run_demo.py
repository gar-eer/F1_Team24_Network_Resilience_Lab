"""Run the full, unshortened demonstration and persist real measurements."""
import asyncio
import json
from pathlib import Path
from bandwidth_throttle_tester.config import validate
from bandwidth_throttle_tester.throttler import Trial
from bandwidth_throttle_tester.metrics import METRICS

async def main():
    config=validate({'scenario':'demo'})
    payload=bytes(range(256))*8192
    results=[]
    for strategy in config['strategies']:
        result=await Trial(payload,config,strategy).run()
        results.append(result)
        print(f"{strategy}: {result['status']}, {result['elapsed_s']:.2f}s, proxy ingress {result['bytes_sent']:,} bytes, repeated/discarded {result['retransmission_bytes']:,}, retries {result['retry_count']}, hash {result['integrity']}",flush=True)
    assert results[0]['status']=='failed'
    assert all(r['integrity'] for r in results[1:])
    assert all(len(r['recoveries'])==1 for r in results[1:])
    assert results[2]['retransmission_bytes']<results[1]['retransmission_bytes']
    out=Path('validation')
    out.mkdir(exist_ok=True)
    (out/'demo-results.json').write_text(json.dumps({'config':config,'metric_definitions':METRICS,'results':results},indent=2),encoding='utf-8')
    print('Full demo assertions passed. Evidence: validation/demo-results.json',flush=True)

if __name__=='__main__':asyncio.run(main())
