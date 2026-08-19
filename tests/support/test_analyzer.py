import asyncio


class TestAnalyzer:
    async def analyze(self, audio: bytes) -> dict:
        await asyncio.sleep(0)
        return {
            "label": "normal",
            "suspicion_score": 0.1,
            "reference_segments": [],
            "guidance": "검토가 필요한 경우 금융기관 공식 채널로 확인하세요.",
        }
