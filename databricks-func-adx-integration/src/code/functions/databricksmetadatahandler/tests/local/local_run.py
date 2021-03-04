from __app__.metadatahandler.__init__ import main
from __app__.metadatahandler.__init__ import logging

if __name__ == "__main__": # pragma: no cover
    sample_msg = """
    {
        "eventType": "Microsoft.Storage.BlobCreated",
        "data": {
            "api": "PutBlob",
            "destinationUrl": "https://jasondevingestion.blob.core.windows.net/sdl/splitdata/output_0/_spark_metadata/0"
        },
        "eventTime": "2020-09-07T06:43:03.2126947Z"
    }
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    class StubQueueObj:
        get_body = lambda: (sample_msg.encode('utf-8'))
    main(StubQueueObj)
