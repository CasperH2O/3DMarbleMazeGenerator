from build123d import *
from ocp_vscode import *
from ocp_vscode.utils import create_shader_ball
from threejs_materials import PbrProperties

shader_ball1 = create_shader_ball("shader_ball-wood")
shader_ball1.material = PbrProperties.from_gpuopen(
    "Ivory Walnut Solid Wood",
).scale(3, 3)

shader_ball2 = Pos(30, 0, 0) * create_shader_ball("shader_ball-carbon")
shader_ball2.material = PbrProperties.from_gpuopen(
    "Carbon biColor Coat",
).scale(2, 2)

show(
    shader_ball1,
    shader_ball2,
    studio_texture_mapping=StudioTextureMapping.PARAMETRIC,
)