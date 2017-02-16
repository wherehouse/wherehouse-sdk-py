from lxml import etree
import sets
#import psycopg2 as psql
import sys
from geopy import distance
import gflags


car = set(['motorway','motorway_link',
    'trunk','trunk_link',
    'primary','primary_link',
    'secondary','secondary_link',
    'tertiary','tertiary_link',
    'residential',
    'road'
])


def speed_profile(highway):
    profile = {
        '_default': 30,
        'residential': 25,
        'tertiary': 25,
        'tertiary_link': 25,
        'secondary': 35,
        'secondary_link': 35,
        'primary': 40,
        'primary_link': 40,
        'trunk': 45,
        'trunk_link': 45,
        'motorway': 65,
        'motorway_link': 65,
    }
    try:
        return profile[highway]
    except KeyError:
        return profile['_default']


def capacity_profile(speed, lanes):
    if speed >= 40:
        return int((1700.+10.*speed)*lanes)
    else:
        return int( 1900*lanes*0.92*0.55 )
    return 0


def lane_profile(highway, oneway=False):
    profile = {
        '_default': 2,
        'residential': 2,
        'tertiary': 2,
        'tertiary_link': 2,
        'secondary': 4,
        'secondary_link': 4,
        'primary': 4,
        'primary_link': 4,
        'trunk': 4,
        'trunk_link': 4,
        'motorway': 6,
        'motorway_link': 6,
    }
    try:
        lanes = profile[highway] / 2
        #if oneway:
        #    lanes /= 2
        return lanes
    except KeyError:
        lanes = profile['_default'] / 2
        #if oneway:
        #    lanes /= 2
        return lanes


def inBBox(lon,lat,bbox):
    if (lon >= bbox[0] and lon <= bbox[2] and lat >= bbox[1] and lat <=bbox[3]):
        return True
    return False

def parseOSM(ifname, bbox=[-360,-360,360,360]):
    nodes_all = {}
    ways = {}
    nodes = {}
    print bbox
    # get all of the nodes
    osm = etree.iterparse(ifname, tag='node')
    for event, node in osm:
        id = int(node.get('id'))
        lat = node.get('lat')
        lon = node.get('lon')
        if inBBox(float(lon), float(lat), bbox):
            nodes_all[id] = {'nbrs':[],'coords':[lon,lat]}
        node.clear()

    osm = etree.iterparse(ifname, tag='way')
    for event,way in osm:
        # get way properties
        id = int(way.get('id'))
        highway = None
        name = None
        lanes = None
        speed = None
        oneway = False
        access = True

        for tag in way.iter('tag'):
            tagType = tag.get('k')
            if tagType == 'highway':
                highway = tag.get('v')
            elif tagType == 'name':
                name = tag.get('v')
            elif tagType == 'oneway':
                if tag.get('v') == 'yes':
                    oneway = True
            elif tagType == 'lanes':
                try:
                    lanes = int(tag.get('v')[0])
                except:
                    pass
            elif tagType == 'maxspeed':
                try:
                    speed = int(tag.get('v')[:2])
                except:
                    speed = None
            elif tagType == 'access':
                if tag.get('v') != 'yes':
                    access = False
        speed = speed_profile(highway)
        if lanes == None:
            lanes = lane_profile(highway, oneway=oneway)

        capacity = capacity_profile(speed, lanes)
        # if the way is a road and routable, add it
        # also add all relevant roads

        if (highway in car) and (access):
            temp_way = {'nds':[],
                    'highway':highway,
                    'name':name,
                    'lanes':lanes,
                    'speed':speed,
                    'capacity':capacity,
                    'oneway':oneway,
                    'way_id':id,
                    'geom':None }

            start = True
            for nd in way.iterfind('nd'):
                if start:
                    ndi = int(nd.get('ref'))
                    if ndi in nodes_all:
                        if ndi not in nodes:
                            nodes[ndi] = {'nbrs':[], 
                                          'ways':[id], 
                                          'coords':nodes_all[ndi]['coords']}
                        else:
                            nodes[ndi]['ways'].append(id)
                        temp_way['nds'].append(ndi)
                        start = False
                else:
                    ndj = int(nd.get('ref'))
                    if ndj in nodes_all:
                        if ndj not in nodes:
                            nodes[ndj] = {'nbrs':[ndi], 
                                          'ways':[id], 
                                          'coords':nodes_all[ndj]['coords']}
                        else:
                            nodes[ndj]['nbrs'].append(ndi)
                            nodes[ndj]['ways'].append(id)
                        nodes[ndi]['nbrs'].append(ndj)
                        temp_way['nds'].append(ndj)
                        ndi = ndj

            ways[id]=temp_way
        way.clear()

    return nodes, ways

def cleanNetwork(nodes, ways):
    new_nodes = {}
    new_ways = {}
    for id in ways:
        new_ways[id] = {
            'pieces': [],
            'highway': ways[id]['highway'],
            'name': ways[id]['name'],
            'lanes': ways[id]['lanes'],
            'speed': ways[id]['speed'],
            'capacity': ways[id]['capacity'],
            'oneway': ways[id]['oneway'],
            'way_id': id,
        }
        way_piece = {'s':None,'t':None,'geom':[]}
        for i in xrange(len(ways[id]['nds'])):
            nd = ways[id]['nds'][i]
            way_piece['geom'].append( nodes[nd]['coords'] )

            if way_piece['s'] == None:
                way_piece['s'] = nd
                if nd in new_nodes:
                    new_nodes[nd]['nbrs'].append(nd)
                    new_nodes[nd]['ways'].append(id)
                else:
                    new_nodes[nd] = {'nbrs':[], 
                                     'ways':[id], 
                                     'coords':nodes[nd]['coords']}

            elif way_piece['t'] == None:
                if (len(nodes[nd]['ways']) == 1 and 
                    len(nodes[nd]['nbrs']) == 2):
                    i+=1;
                else:
                    way_piece['t'] = nd
                    new_ways[id]['pieces'].append(way_piece)
                    i+=1;

                    way_piece = {'s':nd,'t':None,'geom':[nodes[nd]['coords']]}

                    if nd in new_nodes:
                        new_nodes[nd]['nbrs'].append(nd)
                        new_nodes[nd]['ways'].append(id)
                    else:
                        new_nodes[nd] = {'nbrs':[], 
                                         'ways':[id],
                                         'coords':nodes[nd]['coords']}

    # re-index all nodes and edges
    nid = 1
    for n in new_nodes.keys():
        new_nodes[n]['nid'] = nid
        nid += 1

    wid = 1
    for w in new_ways.values():
        for p in w['pieces']:
            p['wid'] = wid
            wid += 1
            if not w['oneway']: # if the road isn't one way, leave room for both directions
                wid+=1
    return new_nodes, new_ways

def printNetwork(nodes, ways, outfile, city):
    wfid = open(outfile, 'w')
    wfid.write('\t'.join([
        'city', 'eid','s_nid','t_nid',
        'way_id','s_node_id','t_node_id',
        'highway','name','lanes',
        'speed','capacity',
        'travel_time_free_flow','oneway','geom'])+'\n')
    count = 1
    for w in ways.values():
        for p in w['pieces']:
            line = [city]
            #line.append(str(count)); count+=1
            line.append( str(p['wid']) )
            line.append( str(nodes[p['s']]['nid']) )
            line.append( str(nodes[p['t']]['nid']) )
            line.append( str(w['way_id']) )
            line.append( str(p['s']) )
            line.append( str(p['t']) )
            line.append( str(w['highway']) )
            line.append( "name")
            line.append( str(w['lanes']) )
            line.append( str(w['speed']) )
            line.append( str(w['capacity']) )
            line.append( str(p['travel_time']) )
            line.append( str(int(w['oneway'])) )
            geom = 'LINESTRING ('
            first = True
            for pair in p['geom']:
                if first:
                    geom += str(pair[0])+' '+str(pair[1])
                    first = False
                else:
                    geom += ', '+str(pair[0])+' '+str(pair[1])
            geom += ')'
            line.append(geom)
            wfid.write( '\t'.join(line)+'\n')
            if not w['oneway']:
                line[1] = str(int(line[1])+1)
                s = line[2]
                t = line[3]
                line[2] = t
                line[3] = s
                wfid.write( '\t'.join(line)+'\n')

    wfid.close()

def writeNodeAndEdgeFiles(nodes, ways, nodes_file, edges_file, city):
    wedge = open(edges_file, 'w')
    wedge.write('eid source target dir capacity speed_mph cost_time\n')
    wnode = open(nodes_file, 'w')
    wnode.write('nid lon lat node_id\n')

    distance.VincentyDistance.ELLIPSOID = 'WGS-84'
    d = distance.distance

    for n in nodes.keys():
        nid = nodes[n]['nid']
        wnode.write(str(nid)+' '+str(nodes[n]['coords'][0])+' '+str(nodes[n]['coords'][1])+' '+str(n)+'\n')
    wnode.close()

    for w in ways.values():
        for p in w['pieces']:
            wid = p['wid']
            s = str(nodes[p['s']]['nid'])
            t = str(nodes[p['t']]['nid'])
            oneway = str(int(w['oneway']))
            capacity = str(w['capacity'])
            speed = str(w['speed'])
            cost_length = 0
            for i in xrange(len(p['geom'])-1):
                xy1 = p['geom'][i]
                xy2 = p['geom'][i+1]
                cost_length += d([xy1[1],xy1[0]],[xy2[1],xy2[0]]).km
            cost_time = 60.0*cost_length/(w['speed']*1.60934)
            p['travel_time'] = cost_time
            cost_time = str(cost_time)
            wedge.write(' '.join([str(wid),s,t,oneway,capacity,speed,cost_time])+'\n')
            if not w['oneway']:
                wedge.write(' '.join([str(wid+1),t,s,oneway,capacity,speed,cost_time])+'\n')
    wedge.close()

    return nodes, ways

def getConnectedSubgraph(G):
    subgraphs=nx.strongly_connected_component_subgraphs(G)
    n=0
    ni=0
    gid=nx.get_edge_attributes(G,'gid')
    for index, item in enumerate(subgraphs):
      if n>item.size():
        continue
      else:
        n=item.size()
        ni=index
    Gsub=subgraphs[ni]
    gids=nx.get_edge_attributes(Gsub,'gid')
    return Gsub


def makeRoadNetworkFromFiles(fedges, fnodes):
    G = nx.DiGraph() # road networks are directed
    # Read the nodes.
    nodes = np.genfromtxt(fnodes,delimiter=' ',skip_header=1) # reading from file
    for i in xrange(len(nodes)):
        nid = int(nodes[i,0]) # nodeid
        lon = float(nodes[i,1]) # longitude
        lat = float(nodes[i,2]) # latitude
        G.add_node(nid,{"nid":nid,"lon":lon,"lat":lat})

    # Read the edges.
    # gid source target dir capacity speed_mph cost_time
    data = np.genfromtxt(fedges, delimiter=' ', skip_header=1)
    for i in xrange(len(data)):
      gid = int(data[i,0])
      s = int(data[i,1])
      t = int(data[i,2])
      direc = int(data[i,3])
      cap = int(data[i,4])
      speed_mph = int(data[i,5])
      cost_time = float(data[i,6])
      G.add_weighted_edges_from([(s,t,{'gid':gid,'cap':cap,'speed':speed_mph,'free_travel_time':cost_time,'length':speed_mph*cost_time*1.609344/60})])
      if direc == 0:
        G.add_weighted_edges_from([(t,s,{'gid':gid,'cap':cap,'speed':speed_mph,'free_travel_time':cost_time,'length':speed_mph*cost_time*1.609344/60})])
    return G


gflags.DEFINE_string('input_osm_file', '', 'an OSM data file')
gflags.DEFINE_string('city', '', 'the name of the city')
gflags.DEFINE_string('output_osm_file', '', 
                     'an output file to write osm data to')
gflags.DEFINE_string('output_edges_file', '', 'an edges file to write to')
gflags.DEFINE_string('output_nodes_file', '', 'an nodes file to write to')
gflags.DEFINE_string('bbox', '-360,-360,360,360', 
                     'a bounding box lon_min,lat_lin,lon_max,lat_max')

FLAGS = gflags.FLAGS

def main(argv):
    # Parse those flags
    try:
        argv = FLAGS(argv)
    except ValueError as e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)
    bbox = [float(s) for s in FLAGS.bbox.split(',')]

    nodes,ways = parseOSM(FLAGS.input_osm_file, bbox=bbox)
    new_nodes,new_ways = cleanNetwork(nodes, ways)
    new_nodes, new_ways = writeNodeAndEdgeFiles(new_nodes,
                                                new_ways,
                                                FLAGS.output_nodes_file, 
                                                FLAGS.output_edges_file,
                                                FLAGS.city)
    printNetwork(new_nodes, new_ways, FLAGS.output_osm_file, FLAGS.city)

if __name__=="__main__":
    main(sys.argv)
