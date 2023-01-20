from elasticsearch import Elasticsearch
import certifi
from http.client import HTTPSConnection
from base64 import b64encode
import json


def main():
    userAndPass = b64encode(b"username:password").decode("ascii")
    headers = { 'Authorization' : 'Basic %s' %  userAndPass }
    print(headers)
    # 10.55.36.117
    es = Elasticsearch(['https://bklair:TheATeam123@agrewcpxyo003v.rbi.web.ds:443'])
    # 'elk-stack-oat.adaptris.net'
    # es = Elasticsearch(
    #     ['10.55.36.117'],
    #     http_auth=('bklair', 'TheAteam123'),
    #     scheme="https",
    #     port=443,
    #     http_compress=True
    # )
    # Check status
    try:
        health_check_result = es.cluster.health()
        print("Elastic search health check returned: {}".format(json.dumps(health_check_result)))
    except Exception as ex:
        print(ex)
    #
    # try:
    #     es = Elasticsearch(
    #         ['agrewcmono003v.rbi.web.ds', 'elk-stack-oat.adaptris.net'],
    #         http_auth=('bklair', 'TheAteam123'),
    #         port=9200,
    #         use_ssl=True,
    #         verify_certs=True,
    #         ca_certs=certifi.where(),
    #     )
    #     print("Connected", es.info())
    # except Exception as ex:
    #     print("Error:", ex)


if __name__ == '__main__':
    main()
