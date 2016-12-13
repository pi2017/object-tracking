import argparse
import logging
import sys
import thread
import time

from pyfirmata import Arduino

import servo
from  grpc_source import GrpcDataSource
from http_source import HttpDataSource

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--grpc", default=False, action="store_true", help="Run gRPC server [false]")
    parser.add_argument("-o", "--http", default=False, action="store_true", help="Run HTTP server [false]")
    parser.add_argument("-t", "--test", default=False, action="store_true", help="Test mode [false]")
    parser.add_argument("-c", "--calib", default=False, action="store_true", help="Calibration mode [false]")
    parser.add_argument("-m", "--middle", default=15, type=int, help="Middle percent [15]")
    parser.add_argument("-p", "--port", default="ttyACM0", type=str,
                        help="Arduino serial port [ttyACM0] (OSX is cu.usbmodemX)")
    parser.add_argument('-v', '--verbose', default=logging.INFO, help="Include debugging info",
                        action="store_const", dest="loglevel", const=logging.DEBUG)
    args = vars(parser.parse_args())

    logging.basicConfig(stream=sys.stdout, level=args['loglevel'],
                        format="%(funcName)s():%(lineno)i: %(message)s %(levelname)s")
    # logging.basicConfig(filename='error.log', level=args['loglevel'],
    #                    format="%(funcName)s():%(lineno)i: %(message)s %(levelname)s")

    middle = int(args["middle"])
    logging.info("Middle percent: {0}".format(middle))

    if args["grpc"] or args["test"]:
        source = GrpcDataSource(50051)
    elif args["http"]:
        source = HttpDataSource(8080)
    else:
        source = None

    try:
        if source:
            thread.start_new_thread(source.start, ())
    except BaseException as e:
        logging.error("Unable to start data source [{0}]".format(e))

    if args["test"]:
        for i in range(0, 1000):
            x_val = source.get_x()
            y_val = source.get_y()
            print("Received location {0}: {1}, {2} {3}x{4}".format(i, x_val[0], y_val[0], x_val[1], y_val[1]))
        print("Exiting...")
        sys.exit(0)

    # Setup firmata client
    port = "/dev/" + args["port"]
    try:
        board = Arduino(port)
        logging.info("Connected to arduino at: {0}".format(port))
    except OSError as e:
        logging.error("Failed to connect to arduino at {0} - [{1}]".format(port, e))
        sys.exit(0)

    # Create servos
    servo_x = servo.Servo(board, "X servo", "d:5:s", middle, lambda: source.get_x(), True)
    servo_y = servo.Servo(board, "Y Servo", "d:6:s", middle, lambda: source.get_y(), False)

    if args["calib"]:
        servo.Servo.calibrate(source, servo_x, servo_y)
        print("Exiting...")
        board.exit()
    else:
        try:
            thread.start_new_thread(servo_x.start, ())
        except BaseException as e:
            logging.error("Unable to start controller for {0} [{1}]".format(servo_x.name(), e))

        try:
            thread.start_new_thread(servo_y.start, ())
        except BaseException as e:
            logging.error("Unable to start controller for {0} [{1}]".format(servo_y.name(), e))

        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt as e:
            print("Exiting...")