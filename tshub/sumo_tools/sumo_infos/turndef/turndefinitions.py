'''
@Author: Karol Stosiek
@Date: 2021-12-01 21:47:51
@Description: 来自 tools/turn-defs/turndefinitions.py
@LastEditTime: 2023-08-31 20:03:42
'''
import sys
import os
from loguru import logger

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib


class TurnDefinitions():
    """ Represents a connection of turn definitions. 
    """
    def __init__(self) -> None:
        """ Constructor. """
        self.turn_definitions = {}

    def add(self, source, destination, probability):
        """ Adds a turn definition. If the given turn definition is already
            defined (in regard to source and destination), issues
            a warning. """

        logger.debug("SIM: Adding turn definition for %s -> %s "
                          "with probability %f" % (source, destination, probability))

        if source not in self.turn_definitions:
            self.turn_definitions[source] = {}

        if destination not in self.turn_definitions[source]:
            self.turn_definitions[source][destination] = 0

        self.turn_definitions[source][destination] += probability

        if self.turn_definitions[source][destination] > 100:
            logger.warning("SIM: Turn probability overflow: %f; lowered to 100" %
                                (self.turn_definitions[source][destination]))
            self.turn_definitions[source][destination] = 100

    def get_sources(self):
        """ Returns all of the turn definitions incoming edges. The result
            will be sorted in alphabetical. """

        sources = sorted(self.turn_definitions.keys())
        return sources

    def get_destinations(self, source):
        """ Returns all of the turn definition's outgoing edges achievable
            from given source. The turn_definition_source must
            have been added before. The result will be sorted in alphabetical
            order."""

        destinations = sorted(self.turn_definitions[source].keys())
        return destinations

    def get_turning_probability(self,
                                source,
                                destination):
        """ Returns the turning probability related to the given
            turn definition. The source and destination must have
            been added before. """

        return self.turn_definitions[source][destination]

    def __eq__(self, other):
        """ Compares this and given object for equality.  """

        if other is None or other.__class__ is not TurnDefinitions:
            logger.debug("SIM: Checking for equality with "
                              "non-TurnDefinitions object")
            return False

        return self.turn_definitions == other.turn_definitions


def from_connections(input_connections):
    """ Creates a TurnDefinitions object from given Connections' object. 
    """
    turn_definitions = TurnDefinitions()
    for source in input_connections.get_sources():
        for source_lane in input_connections.get_lanes(source):
            for destination in input_connections.get_destinations(source,
                                                                  source_lane):
                weight = input_connections.calculate_destination_weight(source,
                                                                        source_lane, destination)

                logger.debug("SIM: Adding connection %s -> %s (%f)" %
                             (source, destination, weight))

                turn_definitions.add(source,
                                     destination,
                                     weight)

    return turn_definitions


def to_xml(turn_definitions, begin, end):
    """ Transforms the given TurnDefinitions object into a string
        containing a valid SUMO turn-definitions file. """

    logger.info("SIM: Converting turn definitions to XML")
    logger.debug("SIM: Turn definitions sources number: %i" %
                 (len(turn_definitions.get_sources())))

    turn_definitions_xml = sumolib.xml.create_document("turns")

    interval_element = turn_definitions_xml.addChild("interval")
    interval_element.setAttribute("begin", begin)
    interval_element.setAttribute("end", end)

    for source in turn_definitions.get_sources():
        logger.debug("SIM: Converting turn definition with source %s" % (source))

        for destination in turn_definitions.get_destinations(source):
            edgeRelation = interval_element.addChild("edgeRelation", {"from": source})
            probability = turn_definitions.get_turning_probability(source,
                                                                   destination)

            logger.debug("SIM: Converting turn definition destination %s "
                         "with probability %f" % (destination, probability))
            edgeRelation.setAttribute("to", destination)
            edgeRelation.setAttribute("probability", "%.10g" % probability)

    return turn_definitions_xml.toXML()
