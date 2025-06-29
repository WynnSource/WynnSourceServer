from app.domain.response.v1.data import Data
from app.domain.response.v1.response import StatusResponse, V1Response

V1_Status_Response = StatusResponse()
V1_Empty_Response = V1Response(data=Data())
