import bpybuild

bpybuild.create_python_module()

try:

    import bpy

except:

    print("Failed!")

else:

    print("Succeeded!")