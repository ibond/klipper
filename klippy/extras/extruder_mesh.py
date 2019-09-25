# Support for servos
#
# Copyright (C) 2017,2018  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import math
import logging

SERVO_SIGNAL_PERIOD = 0.020
PIN_MIN_TIME = 0.100


class ExtruderMesh:
    def __init__(self, config):
        self.printer = config.get_printer()

        self.min_x = 0
        self.max_x = 300
        self.min_y = 0
        self.max_y = 300
        self.points_x = 5
        self.points_y = 5

        self.points = [
            0.241, 0.277, 0.282, 0.283, 0.262,
            0.183, 0.210, 0.221, 0.220, 0.201,
            0.114, 0.133, 0.141, 0.140, 0.126,
            0.054, 0.048, 0.046, 0.047, 0.049,
            0.027, 0.012, 0.000, 0.003, 0.018
        ]

        self.gcode = self.printer.lookup_object('gcode')
        self.printer.register_event_handler("klippy:ready", self.handle_ready)

        self.enabled = True

        self.gcode.register_command(
            'ENABLE_EXTRUDER_MESH', self.cmd_ENABLE_EXTRUDER_MESH)
        self.gcode.register_command(
            'DISABLE_EXTRUDER_MESH', self.cmd_DISABLE_EXTRUDER_MESH)

    def handle_ready(self):
        self.next_transform = self.gcode.set_move_transform(self, force=True)

    def move(self, newpos, speed):
        if self.enabled and self.gcode.extruder.get_heater().can_extrude:
            offset = self._calc_extruder_offset(newpos)
            x, y, z, e = newpos

            self.next_transform.move([x, y, z, e + offset], speed)
        else:
            self.next_transform.move(newpos, speed)
    
    def get_position(self):
        return self.next_transform.get_position()

    # Calculate the extruder offset for the given position.
    def _calc_extruder_offset(self, pos):
        x, y, z, e = pos

        x = max(self.min_x, min(self.max_x, x))
        y = max(self.min_y, min(self.max_y, y))

        lookup_x = ((x - self.min_x) /
                    float(self.max_x - self.min_x)) * (self.points_x - 1)
        lookup_y = ((y - self.min_y) /
                    float(self.max_y - self.min_y)) * (self.points_y - 1)

        ix0 = int(math.floor(lookup_x))
        ix1 = int(math.ceil(lookup_x))
        iy0 = int(math.floor(lookup_y))
        iy1 = int(math.ceil(lookup_y))

        #x0y0 = self.points[iy0 * self.points_x + ix0]
        #x0y1 = self.points[iy1 * self.points_x + ix0]
        #x1y0 = self.points[iy0 * self.points_x + ix1]
        #x1y1 = self.points[iy1 * self.points_x + ix1]
        
        # test points are transposed
        x0y0 = self.points[ix0 * self.points_x + iy0]
        x0y1 = self.points[ix1 * self.points_x + iy0]
        x1y0 = self.points[ix0 * self.points_x + iy1]
        x1y1 = self.points[ix1 * self.points_x + iy1]

        px = math.modf(lookup_x)[0]
        py = math.modf(lookup_y)[0]

        xa = ((1-px) * x0y0) + (px * x1y0)
        xb = ((1-px) * x0y1) + (px * x1y1)

        result = ((1-py) * xa) + (py * xb)

        logging.debug("extruder_mesh: (%.2f,%.2f,%.4f) -> %f" % (x, y, e, result))
        logging.debug("extruder_mesh: (%.2f,%.2f)" % (lookup_x, lookup_y))
        logging.debug("extruder_mesh: (%d,%d,%d,%d)" % (ix0, ix1, iy0, iy1))
        logging.debug("extruder_mesh: (%.3f,%.3f,%.3f,%.3f)" % (x0y0, x1y0, x0y1, x1y1))

        return result

    def cmd_ENABLE_EXTRUDER_MESH(self, params):
        self.enabled = True

    def cmd_DISABLE_EXTRUDER_MESH(self, params):
        self.enabled = False


def load_config(config):
    return ExtruderMesh(config)
