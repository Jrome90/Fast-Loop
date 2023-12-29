def split_edge_loop(bm: BMesh, side=1, slide_verts=None, loops=None):
    def create_new_vert(vert: BMVert, edge: BMEdge):
        new_vert = bm.verts.new(vert.co)
        
        other_vert_co = edge.other_vert(vert).co
        new_vert.co = vert.co.lerp(other_vert_co, 0.01)
        new_vert.index = next(global_vert_index_counter)

        return new_vert
    
    def is_corner_vert_inset(vert: BMVert):
        data = separate_vert_data.get(vert, None)
        if data is not None:
            #if data.face_slide[side][0] and data.face_slide[side][1] is not None:
            return data.face_slide[side][0] == VertSlideType.FACE_INSET
        return False
    
    def is_corner_vert_outset(vert: BMVert):
        data = separate_vert_data.get(vert, None)
        if data is not None:
            return data.face_slide[side][0] == VertSlideType.FACE_OUTSET
        return False

    def is_corner_vert_at_face(vert: BMVert, face: BMFace):
        data = separate_vert_data.get(vert, None)
        if data is not None:
            return (is_corner_vert_inset(vert) or is_corner_vert_outset(vert)) and data.face_slide[side][1] == face
        return False

    ensure(bm)
    if slide_verts is None:
        slide_verts: Dict[int , EdgeVertexSlideData] = {}
        if loops is not None:
            edges = loops #[edge for edge in loops if edge is not None and edge.select]
        slide_verts, loops = eso.calculate_edge_slide_directions(edges[0], edges)
    # side = 1
    dupe_verts = set()
    edge_loop_a = []

    verts_to_split = []
    edges_to_split_with =  {}
    vert_edge_lookup = {}
    loop_a_verts = []

    separate_vert_data = {}

    vert_to_dir_lookup = {}

    data: EdgeVertexSlideData
    prev_vert = None
    prev_edge = None
    for i, (data, edge_index) in enumerate(zip(slide_verts.values(), loops.values())):
        bm_vert = bm.verts[data.vert]
        loop_edge:BMEdge = None
        if edge_index is not None:
            loop_edge = bm.edges[edge_index]
            # prev_loop_edge_index = edge
            vert_edge_lookup[bm_vert] = [loop_edge, prev_edge]
            prev_vert = bm_vert
            prev_edge = loop_edge
            
        else:
            loop_edge = loops[prev_vert.index]
            bm_loop_edge = bm.edges[loop_edge]
            vert_edge_lookup[bm_vert] = [bm_loop_edge, prev_edge]

        edge_loop_a.append(loop_edge)
        
        if bm_vert not in dupe_verts:
            # print(f"vert 1: {vert_1.index}; other vert a :{data.vert_side[0].index} other vert b :{data.vert_side[1].index}")
            loop_a_verts.append(bm_vert.index)
            # loop_a.add(vert_1)
            # loop_a_vert_to_index[vert_1] = vert_1.index
            # verts_to_split.append(bm_vert)

            side_a = bm.verts[data.vert_side[0]] if data.vert_side[0] is not None else None
            edge_a = bm.edges.get([bm_vert, side_a]) if side_a is not None else None
            side_b = bm.verts[data.vert_side[1]] if data.vert_side[1] is not None else None
            edge_b = bm.edges.get([bm_vert, side_b]) if side_b is not None else None
            
            s = [edge_a, edge_b]
            #edges_to_split_with[bm_vert] = s


                # print(f"split_verts: {vs}")
            vert_to_dir_lookup[bm_vert.index] = (data.dir_side[0], data.dir_side[1]) #(data.dir_side[1], data.dir_side[0]) if side == 0 else (data.dir_side[0], data.dir_side[1])
            dupe_verts.add(bm_vert)

            loop_edge1 = vert_edge_lookup[bm_vert][0]
            prev_edge1 = vert_edge_lookup[bm_vert][1]

            separate_vert_data[bm_vert] = VertSeparateData(loop_edge1, prev_edge1, s, \
            (data.dir_side[0], data.dir_side[1]), (data.face_slide[0], data.face_slide[1]))
            #print(vert_data)
            #print(f" edge_a: {bm.edges.get([vert_1 ,data.vert_side[0]])}")
            #print(f" edge_b: {bm.edges.get([vert_1 ,data.vert_side[1]])}")


    loop_b_verts = []   
    new_edges = []
    prev_vert = None
    delete_edges = []
    old_faces = []
    new_faces = set()

    faces_to_make = defaultdict(dict)
    faces_to_make2 = defaultdict(dict)

    full_loop = False
    indicies = list(edges_to_split_with.keys())
    if len (edges_to_split_with) > 2 and get_face_with_edges([edges_to_split_with[indicies[0]][side], edges_to_split_with[indicies[-1]][side]]):
        full_loop = True

    verts = list(separate_vert_data.keys())
    vert_data_list = list(separate_vert_data.values())
    vert_data: VertSeparateData
    visited = defaultdict(set)
    visited_new = defaultdict(set)
    orig_vert_to_new_vert_map = {}
    face_to_direction_edge_map = {}
    face_to_corner_vert_map = defaultdict(dict)
    corner_vert_to_face_map = defaultdict(dict)

    direction_edge_new_verts_map = defaultdict(lambda: defaultdict(list))


    last_face = None
    update_verts = defaultdict()
    update_verts = defaultdict()
    start_vert = None
    end_vert = None


    
    for i, (vert, vert_data) in enumerate(zip(verts, vert_data_list)):
        edges = [vert_data.edge, vert_data.prev_edge]
        direction_edge = vert_data.direction_edges[side]

        orig_vert_to_new_vert_map[vert] = create_new_vert(vert, direction_edge)

    vert: BMVert
    for i, (vert, vert_data) in enumerate(zip(verts, vert_data_list)):
        edges = [vert_data.edge, vert_data.prev_edge]
        direction_edge = vert_data.direction_edges[side]
        next_direction_edge = vert_data_list[(i+1) % len(vert_data_list)].direction_edges[side]
        corner_vert = is_corner_vert_inset(vert) or is_corner_vert_outset(vert) #vert_data.face_slide[side]

        if is_corner_vert_outset(vert):
            # exclude_face = get_face_with_edges(edges)
            # vert_faces = set(list(vert.link_faces))
            # vert_faces.discard(exclude_face)
            # for face in vert_faces:
            #     sep_vert = bmesh.utils.face_vert_separate(face, vert)
                #bmesh.utils.vert_splice(sep_vert, orig_vert_to_new_vert_map[vert])
            # vert_sep_edges = list(set(list(vert.link_edges)).difference(edges))
            # bmesh.utils.vert_separate(vert, vert_sep_edges)

            if vert in orig_vert_to_new_vert_map:
                new_vert = orig_vert_to_new_vert_map[vert]
                loop_b_verts.append(new_vert)
            continue

        #################
        start, end = False, False
        if i == len(vert_data_list) - 1:
            end = True
            end_vert = vert
        elif i == 0:
            start = True
            start_vert = vert
        try:
            new_vert, faces, face_to_other_vert_map = separate_vert2(bm, vert, direction_edge, next_direction_edge, edges, full_loop, prev_vert, corner_vert, start, end)
        except:
            pass
        print("")


        #################################
        # make_faces = None
        # try:
        #     edges, new_vert, new_edge, faces, edges_to_remove, make_faces = separate_vert(bm, vert, direction_edge, next_direction_edge, edges, possible, full_loop, side, prev_vert, is_corner_vert)
        # except:
        #     pass
        # orig_vert_to_new_vert_map[vert] = new_vert

        #faces_to_make.update(faces)
        delete_direction_edge = True
        for i, (face, verts) in enumerate(faces.items()):
            face_to_direction_edge_map[face] = direction_edge
            # other_vert = None
            # if len(verts) == 1:
            #     vert_list = list(verts.keys())
            #     other_vert = direction_edge.other_vert(vert_list[0])
                #if other_vert.select:
                    #print(f"Ned to update: {other_vert.index}")
                    #update_verts[face][other_vert] = None
                #     faces_to_make[face][other_vert] = None #Update later
            keys = list(verts.keys())
            for key in keys:
                if verts[key] is None and key in orig_vert_to_new_vert_map:
                    verts[key] = orig_vert_to_new_vert_map[key]
               
                # if len(keys) > 1:
                #     other_vert = direction_edge.other_vert(key)
                #     if other_vert in orig_vert_to_new_vert_map:
                #         new_vert = orig_vert_to_new_vert_map[other_vert]
                #         print(f"Other vert: {other_vert.index} found with vert {new_vert.index}")
                #         verts[other_vert] = orig_vert_to_new_vert_map[other_vert]


            faces_to_make[face].update(verts)

                # if vert in update_verts:
                #     print(f"Updated vert {vert.index} with {new_vert.index}")
                #     update_verts[vert] = new_vert

            # if face not in direction_edge_new_verts_map:
            if vert in orig_vert_to_new_vert_map:
                new_vert = orig_vert_to_new_vert_map[vert]
                direction_edge_new_verts_map[face][direction_edge].append(new_vert)

                if is_corner_vert_at_face(vert, face.index):
                    face_to_corner_vert_map[face][vert] = None
                    corner_vert_to_face_map[vert][face] = None
                    delete_direction_edge = False
            # else:
            #     direction_edge_new_verts_map[face][direction_edge].append(new_vert)
            if end and i == 0 and not direction_edge.is_boundary:
                last_face = face

        for face, verts in face_to_other_vert_map.items():
            faces_to_make2[face].update(verts)

        # for key, value in make_faces.items():
        #     for vert2, include_vert in make_faces[key].items():
        #         if vert2 not in visited[key]:
        #             faces_to_make[key][vert2] = vert2
    
        #         else:
        #             if vert2 in faces_to_make[key]:
        #                 v = orig_vert_to_new_vert_map[vert2]
        #                 faces_to_make[key][vert2] = v

        #     visited[key].add(vert)
        if delete_direction_edge:
            delete_edges.append(direction_edge)
        # direction_edge.tag = True
        # new_edges.extend(edges)
        if vert in orig_vert_to_new_vert_map:
            new_vert = orig_vert_to_new_vert_map[vert]
            loop_b_verts.append(new_vert)
        # prev_vert = new_vert
        # ignore_verts.add(vert)
        old_faces.extend(faces)
        # for vert in verts_to_split:
        #    if not edges_to_split_with[vert][side].is_valid:
        #         edges_to_split_with[vert][side] = new_edge
       
        # delete_edges.extend(edges_to_remove)
        # if i == 1:
        #     break

    # for i, (face, verts) in enumerate(faces_to_make.items()):
    #     if vert in update_verts:
    #         print(f"Updated vert {vert.index} with {new_vert.index}")
    #         update_verts[vert] = new_vert
    # for face, verts in faces_to_make.items():
    #     verts2 = {}
    #     keys = list(verts.keys())
    #     for key in keys:
    #         if len(keys) > 1:
    #             other_vert = faces_to_make2[face][key]
    #             if other_vert in orig_vert_to_new_vert_map:
    #                 new_vert = orig_vert_to_new_vert_map[other_vert]
    #                 print(f"Other vert: {other_vert.index} found with vert {new_vert.index}")
    #                 verts2[other_vert] = orig_vert_to_new_vert_map[other_vert]
    #     faces_to_make[face].update(verts2)



    new_face_verts = []
    if fill:
        fill_faces(bm, faces_to_make)

    prev_face = None
    dont_delete = set()
    # dict(key: face_index, value : dict(key: bmvert, value: True/False))
    for i, (face_index, vert_group) in enumerate(faces_to_make.items()):
        end = (i == len(faces_to_make) -1)
        verts = []
        # if face_index.index == 3:
        #     continue
        if len(vert_group) > 1: 
            
            bm_face: BMFace = face_index
            # vert_list = list(vert_group.keys())
            # edge = bm.edges.get(vert_list)
            #if edge is None:
            edge = face_to_direction_edge_map[bm_face]
            if edge is not None:
                face_loop = get_face_loop_for_edge(bm_face, edge)

            for loop in bmesh_face_loop_walker(bm_face, face_loop):
                loop_vert = loop.vert
                loop_edge = loop.edge
                skip = False
                other_vert = loop_edge.other_vert(loop_vert)
                if loop_vert in corner_vert_to_face_map and bm_face not in corner_vert_to_face_map[loop_vert]:
                    print(f"{face_index.index} doesnt have vert as a corner {loop_vert.index}")
                    verts.append(loop_vert)
                    print(f"{face_index.index} vert {loop_vert.index}")
                    skip = True

                # elif loop_vert in vert_group and loop_vert not in corner_vert_to_face_map:
                #     edges = [edge for edge in loop_vert.link_edges if edge.select]
                #     if len(edges) == 1:
                #         if other_vert not in corner_vert_to_face_map:
                #             verts.append(loop_vert)
                #             print(f"{face_index.index} verT {loop_vert.index}")

                elif loop_vert not in vert_group:
                    verts.append(loop_vert)
                    print(f"{face_index.index} vert {loop_vert.index}")


                # elif end:
                #     if bm_face not in face_to_corner_vert_map:
                #         edges = [edge for edge in loop_vert.link_edges if edge.select]
                #         if len(edges) == 1:
                #             verts.append(loop_vert)
                #             print(f"{face_index.index} verT {loop_vert.index}")
                    
                # if bm_face not in face_to_corner_vert_map:
                #     edges = [edge for edge in other_vert.link_edges if edge.select]
                #     if len(edges) <= 2:
                #         verts.append(other_vert)
                #         print(f"{face_index.index} verT {other_vert.index}")

                # if loop_vert in vert_group:
                #     if vert_group[loop_vert] is None:
                #         verts.append(loop_vert)
                #         print(f"{face_index.index} vert {loop_vert.index}")
                    

                has_edge = loop_edge in direction_edge_new_verts_map[face_index]
                if has_edge and not skip:
                    # other_Vert = None
                    # if loop_vert in faces_to_make2[bm_face] and bm_face.index == 3:
                    #     other_vert = loop_edge.other_vert(loop_vert)
                    #     new_vert = orig_vert_to_new_vert_map[other_vert]
                    #     direction_edge_new_verts_map[face_index][loop_edge].append(new_vert)

                    inv_map = {v: k for k, v in vert_group.items() if v is not None}
                    new_verts = set(direction_edge_new_verts_map[face_index][loop_edge])

                    for new_vert in direction_edge_new_verts_map[face_index][loop_edge]:
                        if new_vert in inv_map and inv_map[new_vert] == loop.vert:
                            verts.append(new_vert)
                            new_verts.discard(new_vert)
                    if new_verts:
                            verts.append(new_verts.pop())


        # if  1 < len(vert_group) < 3:
        # #     edge_verts, new_verts = vert_group.items()
        # #     # [edge_verts[0], new_verts[0], new_verts[1], edge_verts[1]]
        # #     verts = [edge_verts[1], new_verts[1], new_verts[0], edge_verts[0]]

        #     bm_face = face_index
        #     vert_list = list(vert_group.keys())
        #     edge = bm.edges.get(vert_list)
        #     if edge is None:
        #         edge = face_to_direction_edge_map[bm_face]
            
        #     if edge is not None:
        #         face_loop = get_face_loop_for_edge(bm_face, edge)
        #         # new_vert = vert_group[vert2]
        #         if face_loop is None:
        #             continue

        #         e = face_loop.edge
                
        #         vert1 = vert_list[0]
        #         vert2 = vert_list[1]
        #         skip = False

        #         if prev_face is not None:
        #             set1 = set(vert_list)
        #             set2= set(faces_to_make[prev_face])
        #             diff = set1.difference(set2)
        #             if len(diff) == 0:
        #                 print(f"Both faces {face_index.index}, {prev_face} share new verts")
        #                 new_vert1 = vert_group[vert1]
        #                 new_vert2 = vert_group[vert2]
        #                 verts.extend([vert2, new_vert2, new_vert1, vert1])

        #                 face_loop = face_loop.link_loop_next.link_loop_next
        #                 skip = True
        #             elif len(diff) > 0:
        #                 print(f"Both faces {face_index.index}, {prev_face} some share new verts")


        #         # if face_index == last_face and (prev_face in faces_with_corner_verts and \
        #         # len(faces_with_corner_verts[prev_face]) == 2 and not is_corner_vert(vert1) and not is_corner_vert(vert2)):
        #         #     new_vert1 = vert_group[vert1]
        #         #     new_vert2 = vert_group[vert2]
        #         #     verts.extend([vert2, new_vert2, new_vert1, vert1])

        #         #     face_loop = face_loop.link_loop_next.link_loop_next
        #         #     skip = True
        #         # elif face_index == last_face and not is_corner_vert(vert1) and not is_corner_vert(vert2):
        #         #     new_vert1 = vert_group[vert1]
        #         #     new_vert2 = vert_group[vert2]
        #         #     verts.extend([vert2, new_vert2, new_vert1, vert1])

        #         #     face_loop = face_loop.link_loop_next.link_loop_next
        #         #     skip = True

        #         #TODO: Verts 3 and 5 are fucked: ed_clone_cube_crash2.blend
        #         for loop in bmesh_face_loop_walker(bm_face, face_loop):
        #             if skip:
        #                 if loop.vert == vert1 or loop.vert == vert2:
        #                     break

        #             if loop.vert in vert_group:
        #                 # data = separate_vert_data.get(loop.vert, None)
        #                 # if data is not None:
        #                 #     if not data.face_slide[side]:
        #                 #         verts.append(loop.vert)

        #                 new_vert = vert_group[loop.vert]
        #                 print(f"{face_index.index} vert {new_vert.index}")
        #                 verts.append(new_vert)
                        
        #             else:
        #                 verts.append(loop.vert)
        #                 print(f"{face_index.index} vert {loop.vert.index}")
        
        # elif len(vert_group) > 2:
        #     print(f"FACE: {face_index.index}")
        #     bm_face = face_index
        #     vert_list = list(vert_group.keys())
        #     vert2 = vert_list[0]
        #     edge = face_to_direction_edge_map[bm_face]
        #     face_loop = get_face_loop_for_edge(bm_face, edge)
        #     #new_vert = vert_group[vert2]
        #     e = face_loop.edge

        #     vert1 = vert_list[0]
        #     vert2 = vert_list[1]
        #     skip = False
        #     if not any([is_corner_vert(vert) for vert in vert_list]):
        #         print(f"Face {face_index.index} Has no corner vert(s)")
        #         # new_vert1 = vert_group[vert1]
        #         # new_vert2 = vert_group[vert2]
        #         # verts.extend([vert2, new_vert2, new_vert1, vert1])

        #         # face_loop = face_loop.link_loop_next.link_loop_next
        #         # skip = True

        #     for loop in bmesh_face_loop_walker(bm_face, face_loop):
        #         if skip:
        #             if loop.vert == vert1 or loop.vert == vert2:
        #                 break

        #         other_vert = e.other_vert(vert2)

        #         new_vert = vert_group.get(loop.vert, None)
        #         if new_vert is not None:
        #                 verts.append(new_vert)
        #                 continue

        #         verts.append(loop.vert)
                
        #         # if loop.vert == other_vert and loop.link_loop_next.vert == vert2:
        #         #     print(f"{face_index.index} vert-- {new_vert.index}")
        #         #     verts.append(new_vert)

        #         # elif loop.vert == vert2 and loop.link_loop_next.vert == vert2:
        #         #     #print(f"{face_index} vert-- {new_vert}")
        #         #     print(f"{face_index.index} vert-- {new_vert.index}")
        #         #     verts.append(new_vert)

        #         # elif loop.vert == vert2 and loop.link_loop_next.vert == other_vert:
        #         #     #print(f"{face_index} vert-- {new_vert}")
        #         #     print(f"{face_index.index} vert-- {new_vert.index}")
        #         #     verts.append(new_vert)

        elif len(vert_group) == 1:
            bm_face = face_index
            vert_list = list(vert_group.keys())
            vert2 = vert_list[0]
            edge = face_to_direction_edge_map[bm_face]
            face_loop = get_face_loop_for_edge(bm_face, edge)
            new_vert = vert_group[vert2]
            e = face_loop.edge

            new_vert_added = False
            for loop in bmesh_face_loop_walker(bm_face, face_loop):
                other_vert = e.other_vert(vert2)
                verts.append(loop.vert)
                print(f"{face_index.index} Overt-- {loop.vert.index}")
                
                if is_corner_vert_inset(vert2):
                    continue

                if loop.vert == other_vert and loop.link_loop_next.vert == vert2:
                    print(f"{face_index.index} vert-- {new_vert.index}")
                    verts.append(new_vert)
                    new_vert_added = True

                elif loop.vert == vert2 and loop.link_loop_next.vert == vert2:
                    #print(f"{face_index} vert-- {new_vert}")
                    print(f"{face_index.index} vert-- {new_vert.index}")
                    verts.append(new_vert)
                    new_vert_added = True

                elif loop.vert == vert2 and loop.link_loop_next.vert == other_vert:
                    #print(f"{face_index} vert-- {new_vert}")
                    print(f"{face_index.index} vert-- {new_vert.index}")
                    verts.append(new_vert)
                    new_vert_added = True

            if not new_vert_added:
                print(f"{face_index.index} missed new vert")
        
            
        try:
            face = bm.faces.new(verts)
            face.normal_update()
            for loop in face.loops:
                loop.index = next(global_loop_index_counter)
            # new_faces.add(face)
        except:
            new_face_verts.append(verts)
        
        prev_face = face_index

    for face in old_faces:
        if face.is_valid:
            bm.faces.remove(face)

    edge: BMEdge
    for edge in delete_edges:
        if edge.is_valid:
            print(f"faces for edge {edge.index}-- {[face.index for face in edge.link_faces]} ")
            #if not [face.index for face in edge.link_faces if face.index <= 0]:
            bm.edges.remove(edge)
            #else:
                #print(f"did not del edge-- {edge.index}")
    
    for face_verts in new_face_verts:
        try:
            face = bm.faces.new(face_verts)
            face.normal_update()
            for loop in face.loops:
                loop.index = next(global_loop_index_counter)
        except:
            pass

    bm.verts.index_update()
    loop_b_verts = [vert.index for vert in loop_b_verts]
            
    bm.verts.ensure_lookup_table()

    return loop_a_verts, loop_b_verts, vert_to_dir_lookup