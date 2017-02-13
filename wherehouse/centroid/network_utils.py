from models.raster import Raster

import numpy
import pandas
import shapefile
import random
import os

'''
Utilities for converting road networks into nodes and edges.

created: Feb 13, 2017 by abdinoor
'''

KPH2MPH = 0.621371


def create_network_files(nodes_shapefile, edges_shapefile):

    nodes_output_file = ''.join([os.path.dirname(nodes_shapefile),
                                 'wherehouse_nodes.csv'])
    edges_output_file = ''.join([os.path.dirname(edges_shapefile),
                                 'wherehouse_edges.csv'])
    # Load the nodes shapefile
    nodes_file = shapefile.Reader(nodes_shapefile)

    # Write the header for the output file
    wfid = open(nodes_output_file, 'w')
    wfid.write('nid,lon,lat,external_nid\n')

    # Loop through all the shapes in the nodes shapefile and re-index
    # everything starting with index 1. Then write the node out data
    # out to a file.
    external_nid_2_nid = {}
    for idx, record in enumerate(nodes_file.iterShapeRecords()):
        external_nid_2_nid[record.record[0]] = idx
        # Filter out any nodes at (0, 0)
        if record.shape.points[0][0] == 0:
            continue
        wfid.write('%s,%s,%s,%s\n' % (
            idx,
            record.shape.points[0][0],
            record.shape.points[0][1],
            record.record[0]))
    wfid.close()
    # Open the edges file
    edges_file = shapefile.Reader(edges_shapefile)

    # Write the header for the edges output file.
    wfid = open(edges_output_file, 'w')
    wfid.write('eid,source,target,dir,capacity,'
               'speed_mph,free_flow_travel_time\n')

    # Iterate through all the edge shapes, impute missing columns,
    # and write to file.
    for idx, record in enumerate(edges_file.iterRecords()):
        # Convert speed to MPH for capacity inference.
        speed_mph = numpy.ceil(record[13] * KPH2MPH)
        # Make sure the minimum speed isnt 0 to avoid divide by 0 in
        # travel time cost calculations.
        if speed_mph == 0:
            speed_mph = 0.00001
        # Impute capacity based on speed and number of lanes
        capacity = capacity_profile(speed_mph, record[10])
        # Compute travel time cost in minutes
        cost_time = (record[2] * 0.000621371) / speed_mph * 60
        # Write to file
        data = (idx, external_nid_2_nid[record[0]],
                external_nid_2_nid[record[1]], 0,
                int(capacity), int(speed_mph), cost_time)
        wfid.write('%s,%s,%s,%s,%s,%s,%s\n' % data)
    wfid.close()
    # The original shapefile didn't have the eid column making it hard to
    # join routing output for visualization and validation in QGIS.
    # This loop runs over the shapefile records and adds a field then
    # saves a new shapefile.
    edges_file = shapefile.Reader(edges_shapefile)
    extended_file = shapefile.Writer()
    extended_file.fields = list(edges_file.fields)
    extended_file.field('EID', 'N', 9, 0)

    for idx, record in enumerate(edges_file.iterShapeRecords()):
        new_record = record.record
        new_record.append(idx)
        extended_file.records.append(new_record)
        extended_file._shapes.append(record.shape)

    basename, ext = os.path.splitext(edges_shapefile)
    extended_file.save(basename + "_" + ext)


def capacity_profile(speed, lanes):
    if speed >= 40:
        return int((1700. + 10. * speed) * lanes)
    else:
        return int(1900 * lanes * 0.92 * 0.55)
    return 0


def od_to_intersections(SA2_od_filename,
                        census_raster_file, nodes_shapefile):
    # Load the OD
    od_filename = SA2_od_filename

    # Load a raster file of maping each raster cell to an SA2 it covers
    census_raster = raster.Raster()
    path = census_raster_file
    census_raster.load_data_from_file(path)

    # Load the network nodes
    nodes_file = shapefile.Reader(nodes_shapefile)

    # Loop over all the network nodes and look up which SA2 they are
    # contained in. Maintain a mapping from SA2 to the list of
    # intersection nodes within.
    sa2_2_nid = {}
    for idx, rec in enumerate(nodes_shapefile.iterShapeRecords()):
        lon, lat = rec.shape.points[0]
        sa2 = census_raster.in_poly(lon, lat)
        sa2 = str(sa2)
        # If no SA2 is found, the value will be 0 and we should ignore the node
        if sa2 == 0:
            continue
        if sa2 in sa2_2_nid:
            sa2_2_nid[sa2].append(idx)
        else:
            sa2_2_nid[sa2] = [idx]
    od_inter = {}

    # Loop over all SA2 - SA2 OD pairs. For each SA2 origin and destination,
    # pick a random intersection on each end. Assign a fraction of the
    # SA2 to SA2 flow to this node to node pair.
    for idx, row in od_scaled.dropna().iterrows():
        for i in xrange(int(row.flow_scaled)):
            o_sa2 = row.origin
            d_sa2 = row.destination
            # If we haven't mapped nodes for either the origin to destination
            # just ignore it.
            if o_sa2 not in sa2_2_nid or d_sa2 not in sa2_2_nid:
                continue
            o = random.choice(sa2_2_nid[o_sa2])
            d = random.choice(sa2_2_nid[d_sa2])
            if (o, d) in od_inter:
                od_inter[(o, d)] += row.flow_scaled / int(row.flow_scaled)
            else:
                od_inter[(o, d)] = row.flow_scaled / int(row.flow_scaled)

    basename, ext = os.path.splitext(SA2_od_file)
    od_output_filename = basename + '.intersection' + ext
    wfid = open(od_output_filename, 'w')

    wfid.write('origin_nid,destination_nid,flow\n')
    for (origin_nid, destination_nid), flow in od_inter:
        wfid.write('%d,%d,%0.3f\n' % (origin_nid, destination_nid, flow))
    wfid.close()
