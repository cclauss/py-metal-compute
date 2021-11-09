import sys
from time import time as now
from array import array

import PIL
from PIL.Image import frombuffer

import metalcompute as mc

w,h = 4096, 4096
if len(sys.argv) > 2:
    w,h = int(sys.argv[1]), int(sys.argv[2])
outname = "mandelbrot.png"
if len(sys.argv) > 3:
    outname = sys.argv[3]

outer_iter = 512
inner_iter = 16

start = """
#include <metal_stdlib>
using namespace metal;

kernel void mandelbrot(const device float *uniform [[ buffer(0) ]],
                device uchar4 *out [[ buffer(1) ]],
                uint id [[ thread_position_in_grid ]]) {
    float width = uniform[0];
    float height = uniform[0];
    float2 c = 2.5 * (float2((id%int(width))/width - 0.5, 0.5 - (id/int(width))/height));
    c.x -= 0.7;
    float2 z = c;
    float done = 0.0, steps = 1.0, az = 0.0;
"""

loop_start = f"float maxiter = {inner_iter*outer_iter};for (int iter = {outer_iter};iter>0;iter--){{"

step = """\
    z = float2((z.x * z.x) - (z.y * z.y) + c.x, (2.0 * z.x * z.y) + c.y);
    az = ((z.x*z.x) + (z.y*z.y));
    done = az >= 4.0 ? 1.0 : 0.0;
    if (done > 0.0) { break; }
    steps += 1.0;
"""

end = """}
    z = float2((z.x * z.x) - (z.y * z.y) + c.x, (2.0 * z.x * z.y) + c.y);
    z = float2((z.x * z.x) - (z.y * z.y) + c.x, (2.0 * z.x * z.y) + c.y);
    az = ((z.x*z.x) + (z.y*z.y));
    steps += 2.0;
    steps -= log(log(sqrt(az)))/log(2.0);
    float p = 3.14159 * steps/256.0;
    float3 col = float3(0.5+0.5*sin(p*13.0),
                        0.5+0.5*sin(p*17.0),
                        0.5+0.5*sin(p*19.0));
    if (steps >= maxiter) col *= 0.0; // Outside set
    out[id] = uchar4(uchar3(col*255.),255);
}
"""
print(f"Rendering mandelbrot set using Metal compute, res:{w}x{h}, iters:{outer_iter * inner_iter}")

mc.init()

mc.compile(start + loop_start + step * inner_iter + end, "mandelbrot")
output = bytearray(h*w*4)

start_render = now()
mc.run(array('f',[w,h]), output, w*h)
end_render = now()

mc.release()

print(f"Render took {end_render - start_render:3.6}s")

print(f"Writing image to {outname}")
start_write = now()
frombuffer("RGBA",(w,h),data=output).save(outname)
end_write = now()

print(f"Image encoding took {end_write - start_write:3.6}s")
