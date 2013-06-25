batik_path = 'org.apache.batik.apps.rasterizer.Main'
java_cmd_format = (
        "java {batik_path} {type_option} -d {out_filename} {width_option} "
        "-bg {background} -dpi {dpi} {temp_svg_name}"
)
