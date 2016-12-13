import logging
import time


class Servo:
    def __init__(self, board, name, pin_args, middle, func, forward):
        self._name = name
        self._pin = board.get_pin(pin_args)
        self._middle = middle
        self._func = func
        self._forward = forward
        self._jiggle()

    def _jiggle(self):
        # Provoke an update from the color tracker
        self.write(85, .5)
        self.write(90, 1)

    @property
    def name(self):
        return self._name

    def read(self):
        return self._pin.read()

    def write(self, val, pause=0.0):
        self._pin.write(val)
        if pause > 0:
            time.sleep(pause)

    def start(self):
        middle_pct = (self._middle / 100.0) / 2
        curr_pos = self.read()
        printed = False
        pix_per_deg = 6.5

        while True:
            # Get latest value
            (img_pos, img_total) = self._func()

            # Skip if object is not seen
            if img_pos == -1 or img_total == -1:
                curr_pos = self.read()
                logging.info("No target seen: {0}".format(self._name))
                continue

            midpoint = img_total / 2
            middle_inc = int(img_total * middle_pct / 2)

            if not printed:
                print("Middle window pos:{0} mid:{1} inc:{2}".format(img_pos, midpoint, middle_inc))
                printed = True

            if img_pos < midpoint - middle_inc:
                err = abs((midpoint - middle_inc) - img_pos)
                adj = max(int(err / pix_per_deg), 1)
                new_pos = curr_pos + adj if self._forward else curr_pos - adj
                # print("{0} above moving to {1} from {2}".format(self._name, new_pos, curr_pos))
            elif img_pos > midpoint + middle_inc:
                err = img_pos - (midpoint + middle_inc)
                adj = max(int(err / pix_per_deg), 1)
                new_pos = curr_pos - adj if self._forward else curr_pos + adj
                # print("{0} above moving to {1} from {2}".format(self._name, new_pos, curr_pos))
            else:
                # print "{0} in middle".format(self.name)
                # new_pos = curr_pos
                continue

            delta = abs(new_pos - curr_pos)

            # If you do not pause long enough, the servo will go bonkers
            # Pause for a time relative to distance servo has to travel
            # wait_time = .2 #delta * (3.50 / 180)
            wait_time = .2 if delta > 2 else .075

            if curr_pos != new_pos:
                logging.info("Pos: [{0} Delta: {1}".format(new_pos, delta))

            # Write servo values
            self.write(new_pos, wait_time)

            curr_pos = new_pos

    @staticmethod
    def calibrate(listener, servo_x, servo_y):
        def center_servos(pause=0.0):
            servo_x.write(90, pause)
            servo_y.write(90, pause)

        name = "x"
        servo = servo_x
        while True:
            val = raw_input("{0} {1} ({2}, {3})> ".format(name.upper(),
                                                          servo.read(),
                                                          listener.get_pos("x"),
                                                          listener.get_pos("y")))
            if val.lower() == "q":
                return
            elif val == "c":
                servo.write(90, .5)
            elif val == "C":
                center_servos(.5)
            elif val.lower() == "x":
                name = "x"
                servo = servo_x
            elif val.lower() == "y":
                name = "y"
                servo = servo_y
            elif val.lower() == "s":
                center_servos(1)
                servo.write(0, 2)

                start_pos = -1
                end_pos = -1
                for i in range(0, 180, 1):
                    servo.write(i, .1)
                    if listener.get_pos(name) != -1:
                        start_pos = i
                        break

                if start_pos == -1:
                    print("No target found")
                    continue

                for i in range(start_pos, 180, 1):
                    servo.write(i, .1)
                    if listener.get_pos(name) == -1:
                        break
                    end_pos = i

                total_pixels = listener.get_size(name)
                total_pos = end_pos - start_pos
                pix_deg = round(total_pixels / float(total_pos), 2)
                servo.write(90)
                print("{0} degrees to cover {1} pixels [{2} pixels/degree]".format(total_pos, total_pixels, pix_deg))
            elif len(val) == 0:
                pass
            elif val == "-" or val == "_":
                servo.write(servo.read() - 1, .5)
            elif val == "+" or val == "=":
                servo.write(servo.read() + 1, .5)
            elif val.isdigit():
                servo.write(int(val), .5)
            else:
                print("Invalid input")