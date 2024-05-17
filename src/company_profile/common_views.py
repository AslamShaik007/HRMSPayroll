import requests
from rest_framework.response import Response
from rest_framework.views import APIView

from HRMSApp.renderers import UserRenderer


# Fetch BANK Detailes With IFSCCODE
class FetchBankDetailes(APIView):
    renderer_classes = [UserRenderer]

    def post(self, request):
        data1 = request.data
        ifsc = data1["ifsccode"]
        gett = requests.get(f"https://bank-apis.justinclicks.com/API/V1/IFSC/{ifsc}/")
        data = gett.json()
        return Response({"status": True, "detail": data})
