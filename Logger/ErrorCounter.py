from Telemetry.Telemetry import TeleDatatypes,TelemetryDataSource
from Logger.Logger import Logger

class ErrorCounter(TelemetryDataSource):
    def getTeleData(self):
        return {"error_count" : (Logger.getErrorCount(), TeleDatatypes.INT)}