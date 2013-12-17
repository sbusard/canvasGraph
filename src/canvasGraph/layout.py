import math

class Layout:
    """A graph layout."""
    
    def apply(self, canvas, positions, edges):
        """
        Apply this layout on canvas, with positions of vertices and edges.
        Return a dictionary of new positions for vertices of "positions".
        
        canvas -- the canvas on which operate;
        positions -- a dictionary of vertex -> x,y positions;
        edges -- a list of edges between vertices of positions.        
        """
        raise NotImplementedError("Should be implemented by subclasses.")



class OneStepForceBasedLayout(Layout):
    """
    A force-based layout. Applying only cause one step of the computation
    of the layout. Useful for interactive layouting, each application
    giving the new positions to draw.
    """
    
    def __init__(self):
        self.minSpringLength = 60
        self.springStiffness = 0.1
        self.electricalRepulsion = 500
        self.maxForce = 10


    def _distance_vector_from(self, canvas, positions, vertex, other):
        """
        Return the distance vector from vertex to the other vertex.
        If vertex is at greater position than other,
        the distance vector is negative.
    
        Warning: if vertices overlap, the vector is directed towards vertex.
    
                |               ____
                |      dv      /
          v     /____________>/
               /             /      o
        ______/             |
                            |
        """
    
        xvc, yvc = positions[vertex]
        vw, vh = vertex.dimensions(canvas)
        xoc, yoc = positions[other]
        ow, oh = other.dimensions(canvas)
    
        xv0, yv0, xv1, yv1 = (xvc - vw/2, yvc - vh/2, xvc + vw/2, yvc + vh/2)
        xo0, yo0, xo1, yo1 = (xoc - ow/2, yoc - oh/2, xoc + ow/2, yoc + oh/2)
    
        av = xv1 - xvc      #    +---a-----|
        bv = yv1 - yvc      #    |         |
        ao = xo1 - xoc      #    b        /
        bo = yo1 - yoc      #    |      /
                            #   _|____/
    
        if xoc != xvc:
            m = abs((yoc - yvc) / (xoc - xvc))
        
            dvx = (av * bv) / math.sqrt(av*av * m*m + bv*bv)
            dvx *= -1 if xoc < xvc else 1
        
            dox = (ao * bo) / math.sqrt(ao*ao * m*m + bo*bo)
            dox *= -1 if xoc > xvc else 1
        
            dvy = (av * bv * m) / math.sqrt(av*av * m*m + bv*bv)
            dvy *= -1 if yoc < yvc else 1
        
            doy = (ao * bo * m) / math.sqrt(ao*ao * m*m + bo*bo)
            doy *= -1 if yoc > yvc else 1
    
        else:
            dvx = dox = 0
            dvy = bv
            dvy *= -1 if yoc < yvc else 1
            doy = bo
            doy *= -1 if yoc > yvc else 1
    
        return (xvc + dvx, yvc + dvy, xoc + dox, yoc + doy)

    def _hooke_attraction(self, canvas, positions, vertex, other):
        """
        Return the force produced by the spring between vertex and other,
        applied on vertex.
    
        canvas -- the canvas of interest;
        positions -- the positions of the vertices
                     (a vertex -> x,y position dictionary);
        vertex -- a vertex;
        other -- another vertex.
        """
        dx0, dy0, dx1, dy1 = self._distance_vector_from(canvas, positions,
                                                        vertex, other)
    
        # Use center to check when vertices overlap
        vcx, vcy = positions[vertex]
        ocx, ocy = positions[other]
    
        # Overlap: when overlapping, ignore the force
        if (ocx - vcx) * (dx1 - dx0) < 0 or (ocy - vcy) * (dy1 - dy0) < 0:
            return 0, 0
    
        dx, dy = dx1 - dx0, dy1 - dy0
    
        distance = math.sqrt(dx*dx + dy*dy)
    
        # Spring length is sum of radiuses of vertices
        dcx, dcy = ocx - vcx, ocy - vcy
        length = math.sqrt(dcx*dcx + dcy*dcy) - distance
        length = max(length, self.minSpringLength)
    
        force = -self.springStiffness * (length - distance) / distance
        force = max(min(force, self.maxForce), -self.maxForce)
        fx = force * dx
        fy = force * dy
    
        return fx, fy

    def _coulomb_repulsion(self, canvas, positions, vertex, other):
        """
        Return the electrical force produced by the other vertex on vertex.
    
        canvas -- the canvas of interest;
        positions -- the positions of the vertices
                     (a vertex -> x,y position dictionary);
        vertex -- a vertex;
        other -- another vertex.
        """
        dx0, dy0, dx1, dy1 = self._distance_vector_from(canvas, positions,
                                                        vertex, other)
    
        # Use center to check when vertices overlap
        vcx, vcy = positions[vertex]
        ocx, ocy = positions[other]
    
        # Overlap: when overlapping inverse bounding box
        if (ocx - vcx) * (dx1 - dx0) < 0:
            dx0, dx1 = dx1, dx0
        if (ocy - vcy) * (dy1 - dy0) < 0:
            dy0, dy1 = dy1, dy0
    
        dx, dy = dx1 - dx0, dy1 - dy0
    
        distance = math.sqrt(dx*dx + dy*dy)
    
        force = -self.electricalRepulsion / (distance*distance)
        force = max(min(force, self.maxForce), -self.maxForce)
        fx = force * dx
        fy = force * dy
    
        return fx, fy

    def apply(self, canvas, positions, edges, fixed=None):
        """
        Return the new positions of vertices in positions on canvas,
        given edges between them.
        If fixed is not None, only vertices out of fixed are moved.
    
        canvas -- the canvas on which operate;
        positions -- a dictionary of vertex -> x,y coordinates values;
        edges -- a set of edges between vertices of positions;
        fixed -- a set of vertices.
        """
        if fixed is None:
            fixed = set()
    
        forces = {}
        # Compute forces
        for vertex in positions:
            fx, fy = 0, 0
        
            # Repulsion forces
            for v in positions:
                if vertex != v:
                    cfx, cfy = self._coulomb_repulsion(canvas, positions,
                                                       vertex, v)
                    fx += cfx
                    fy += cfy
        
            # Spring forces
            for edge in edges:
                if edge.origin == vertex or edge.end == vertex:
                    if edge.origin == vertex:
                        other = edge.end
                    else:
                        other = edge.origin
                
                    hfx, hfy = self._hooke_attraction(canvas, positions,
                                                      vertex, other)
                    fx += hfx
                    fy += hfy
        
            forces[vertex] = fx, fy
                
        # Compute new positions
        newPositions = {}
        sumForces = 0
        for vertex in positions:
            fx, fy = forces[vertex]
            x, y = positions[vertex]
            nx = x + fx
            ny = y + fy
            sumForces += math.sqrt(fx*fx + fy*fy)
        
            if vertex not in fixed:
                newPositions[vertex] = nx, ny
            else:
                newPositions[vertex] = x, y
    
        return (newPositions, sumForces/len(newPositions) 
                              if len(newPositions) > 0 else 0)



class ForceBasedLayout(OneStepForceBasedLayout):
    """
    A force-based layout. One application gives the final positions.
    """
    
    def __init__(self):
        super().__init__()
        self.iterationNumber = 1000
        self.forceThreshold = 0.001
    
    def apply(self, canvas, vertices, edges, fixed=None):
        """
        Return the new positions of vertices on canvas,
        given their initial positions and their connected edges.
        Return a dictionary of vertices -> positions pairs, with new positions 
        of the vertices.
        If fixed is not None, only vertices out of fixed are moved.
    
        canvas   -- the canvas on which operate;
        vertices -- a dictionary of vertices -> position pairs, where positions
                    are couples of x,y coordinates
        edges    -- a set of couples (v1, v2)
                    where v1 and v2 belong to vertices;
        fixed    -- a set of vertices.
        """
        np = vertices
        for i in range(self.iterationNumber):
            np, sf = super().apply(canvas, np, edges, fixed=fixed)
            if sf < self.forceThreshold:
                break
        return np