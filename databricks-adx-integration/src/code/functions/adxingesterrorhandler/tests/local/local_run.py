from __app__.errorhandler.__init__ import main

if __name__ == "__main__":
    sample_msg = """
    {
        "eventType": "Microsoft.Storage.BlobCreated",
        "data": {
            "api": "PutBlob",
            "url": ""
        }
    }
    """
    class StubQueueObj:
        get_body = lambda: (sample_msg.encode('utf-8'))
    main(StubQueueObj)
