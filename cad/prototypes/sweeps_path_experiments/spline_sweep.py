from build123d import *
from ocp_vscode import *

def sweep_single_section_profile(profile, path):
    """
    Helper for sweeping a single section ie profile
    """
    with BuildPart() as sweep_path:
        with BuildLine() as path_line:
            add(path)
        # Create the path profile sketch on the work plane
        with BuildSketch(path_line.line^0):
            add(profile)
        sweep(transition=Transition.RIGHT)

    return sweep_path

# Sketch profile L
with BuildSketch() as profile:
    with BuildLine() as line:            
        n1 = Line((-3,-3),(3,-3))
        n2 = Line((-3,-3),(-3,3))
        offset(amount=1, side=Side.RIGHT)
    make_face()

path1_1 = Polyline((-85, 0, 0), (-80, 0, 0), (-75, 0, 0))
sweep1_1 = sweep_single_section_profile(profile,path1_1)

path1_2_polyline = Polyline((-75, 0, 0), (-70, 0, 0), (-70, 10, 0), (-70, 20, 0), (-60, 20, 0), (-60, 30, 0), (-60, 40, 0), (-60, 50, 0), (-60, 50, 10), (-60, 50, 20), (-60, 50, 30), (-50, 50, 30), (-40, 50, 30), (-40, 40, 30), (-30, 40, 30), (-30, 30, 30), (-30, 20, 30), (-30, 10, 30), (-20, 10, 30), (-15, 10, 30))

path1_2_vertices = path1_2_polyline.vertices()
path1_2_spline = Spline((path1_2_vertices[0],path1_2_vertices[-1]),tangents=[path1_2_polyline%0, path1_2_polyline%1])
sweep1_2 = sweep_single_section_profile(profile,path1_2_spline)

path1_3 = Polyline((-15, 10, 30), (-10, 10, 30), (-5, 10, 30))
sweep1_3 = sweep_single_section_profile(profile,path1_3)


path2_1 = Polyline((-20, -75, 30), (-20, -70, 30), (-20, -70, 25))
sweep2_1 = sweep_single_section_profile(profile,path2_1)

path2_2_polyline = Polyline(((-20, -70, 25), (-20, -70, 20), (-20, -70, 10), (-10, -70, 10), (-10, -70, 0), (0, -70, 0), (0, -70, -10), (0, -70, -20), (0, -60, -20), (0, -60, -30), (0, -60, -40), (0, -60, -50), (0, -60, -60), (0, -50, -60), (10, -50, -60), (10, -40, -60), (10, -30, -60), (10, -30, -70), (0, -30, -70), (-10, -30, -70), (-20, -30, -70), (-30, -30, -70), (-40, -30, -70), (-40, -20, -70), (-50, -20, -70), (-50, -10, -70), (-50, 0, -70), (-50, 5, -70)))

path2_2_vertices = path2_2_polyline.vertices()
path2_2_spline = Spline((path2_2_vertices[0],path2_2_vertices[-1]),tangents=[path2_2_polyline%0, path2_2_polyline%1])
sweep2_2 = sweep_single_section_profile(profile,path2_2_spline)

path2_3 = Polyline((-50, 5, -70), (-50, 10, -70), (-45, 10, -70))
sweep2_3 = sweep_single_section_profile(profile,path2_3)



show_all()