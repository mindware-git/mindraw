"""
MindDraw Addon - Blender 5.0 Grease Pencil Integration

IMPORTANT NOTES FOR BLENDER 5.0 GREASE PENCIL API:

=== DATA STRUCTURE CHANGES ===
1. Frame -> Drawing -> Strokes hierarchy:
   - OLD: frame.strokes (ERROR: AttributeError)
   - NEW: frame.drawing.strokes ✓

2. Point coordinates:
   - OLD: point.co (ERROR: AttributeError)
   - NEW: point.position ✓

3. Layer access:
   - OLD: layers.active returns string name
   - NEW: layers.active returns GreasePencilLayer object directly
   - Use: active_layer.name to get name string

4. Collection access:
   - ERROR: bpy_prop_collection.get(key) when key is object, not string
   - FIX: Use direct indexing or check object types first

=== CRITICAL API USAGE ===
1. Mode detection:
   - Draw mode: context.mode == 'PAINT_GREASE_PENCIL'
   - Edit mode: context.mode.startswith('EDIT_')

2. Object selection:
   - Use: bpy.context.selected_objects for stable access
   - Filter: [obj for obj in context.selected_objects if obj.type == 'GREASEPENCIL']

3. Grease Pencil access:
   - Use: bpy.context.grease_pencil for stable access
   - Layers: gp.layers.active (returns object)
   - Active layer: gp.layers.active.name (returns string)

4. Stroke creation:
   - API: bpy.ops.grease_pencil.brush_stroke(stroke=points)
   - Point format: (x, y, z, pressure, strength)
   - Circle generation: 32 segments for smooth circle

=== ERROR RESOLUTION EXPERIENCE ===
1. Always verify attributes with dir() in terminal before use
2. Check object types when using collection methods
3. Use try-except blocks for API compatibility
4. Remove all icons for Blender 5.0 compatibility

=== CIRCLE STROKE CREATION ===
1. Generate 32 points: for i in range(33) # +1 to close circle
2. Calculate coordinates:
   - x = radius * cos(2π * i / 32)
   - y = radius * sin(2π * i / 32)
3. Point format: (x, y, z, pressure, strength)
4. Only show button in Draw mode: if context.mode == 'PAINT_GREASE_PENCIL'

=== DEBUGGING TIPS ===
1. Use terminal to test API calls before implementation
2. Check context.mode for current mode
3. Verify object types with obj.type
4. Use hasattr() for attribute existence checks
"""

import bpy
import sys
import io
import socket
import threading

# ============ COMMENTED OUT OLD IMPORTS ============
# import os
# import math
# import json
# from typing import List
# from bpy.types import Panel, Operator, PropertyGroup
# from bpy.props import StringProperty
# from bpy_extras.io_utils import ImportHelper

bl_info = {
    "name": "MindDraw Addon",
    "author": "Mindware",
    "version": (0, 0, 1),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > MindDraw",
    "description": "MCP Socket Server for Python command execution",
    "category": "Development",
}

# Global variables for socket server
server_socket = None
server_thread = None
is_running = False


def socket_server_thread():
    """Socket server thread function to handle client connections"""
    global is_running

    HOST = "localhost"
    PORT = 8765

    print(f"[MindDraw] Starting socket server on {HOST}:{PORT}")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            print(f"[MindDraw] Socket server listening on {HOST}:{PORT}")

            while is_running:
                try:
                    # Set timeout to allow checking is_running flag
                    s.settimeout(1.0)
                    conn, addr = s.accept()
                    print(f"[MindDraw] Connected by {addr}")

                    # Handle client connection
                    handle_client(conn)

                except socket.timeout:
                    # Timeout is normal, allows checking is_running
                    continue
                except Exception as e:
                    if is_running:
                        print(f"[MindDraw] Error accepting connection: {e}")
                    break

    except Exception as e:
        print(f"[MindDraw] Socket server error: {e}")

    print("[MindDraw] Socket server stopped")


def handle_client(conn):
    """Handle individual client connection"""
    try:
        with conn:
            while is_running:
                # Receive data from client
                data = conn.recv(4096)
                if not data:
                    break

                # Decode and execute Python code
                python_code = data.decode("utf-8")
                print(f"[MindDraw] Received: {python_code[:100]}...")

                try:
                    # Execute Python code
                    old_stdout = sys.stdout
                    sys.stdout = captured_output = io.StringIO()

                    # Create execution context with Blender access
                    exec_context = {
                        "bpy": bpy,
                        "context": bpy.context,
                        "C": bpy.context,
                    }

                    exec(python_code, exec_context)

                    # Get output
                    output = captured_output.getvalue()
                    if not output:
                        output = "Script executed successfully (no output)"

                    # Send result back to client
                    result = f"SUCCESS: {output}"
                    conn.sendall(result.encode("utf-8"))

                except Exception as e:
                    # Send error back to client
                    error_msg = f"ERROR: {str(e)}"
                    conn.sendall(error_msg.encode("utf-8"))

                finally:
                    sys.stdout = old_stdout

    except Exception as e:
        print(f"[MindDraw] Client handling error: {e}")


# class MindDrawProperties(PropertyGroup):
#     """Properties to store script code and output"""

#     script_code: StringProperty(
#         name="Script Code",
#         description="Enter Python code to execute",
#         default="# Enter your Python code here\nprint('Hello from MindDraw!')\n\n# Example: Create a cube\n# bpy.ops.mesh.primitive_cube_add()",
#         options={"TEXTEDIT_UPDATE"},
#     )

#     output_text: StringProperty(
#         name="Output",
#         description="Script execution output",
#         default="Output will appear here...",
#         options={"TEXTEDIT_UPDATE"},
#     )

#     filetalk_directory: StringProperty(
#         name="FileTalk Directory",
#         description="Directory for file-based communication",
#         default="",
#         subtype="DIR_PATH",
#     )

#     json_file_path: StringProperty(
#         name="JSON File",
#         description="Path to JSON file for import/export",
#         default="",
#         subtype="FILE_PATH",
#     )


# class MINDDRAW_OT_execute_script(Operator):
#     """Execute the Python script and show output"""

#     bl_idname = "mindraw.execute_script"
#     bl_label = "Execute Script"
#     bl_options = {"REGISTER", "UNDO"}

#     def execute(self, context: bpy.types.Context) -> set[str]:
#         props: MindDrawProperties = context.scene.mindraw_props

#         if not props.script_code.strip():
#             self.report({"WARNING"}, "No script to execute")
#             return {"CANCELLED"}

#         # Capture stdout
#         old_stdout = sys.stdout
#         sys.stdout = captured_output = io.StringIO()

#         try:
#             # Execute the script with Blender context
#             exec_context = {
#                 "bpy": bpy,
#                 "context": context,
#                 "C": context,
#             }

#             exec(props.script_code, exec_context)

#             # Get the output
#             output = captured_output.getvalue()
#             if output:
#                 props.output_text = output
#             else:
#                 props.output_text = "Script executed successfully (no output)"

#             self.report({"INFO"}, "Script executed successfully")

#         except Exception as e:
#             error_msg = f"Error: {str(e)}"
#             props.output_text = error_msg
#             self.report({"ERROR"}, error_msg)

#         finally:
#             # Restore stdout
#             sys.stdout = old_stdout

#         return {"FINISHED"}


# class MINDDRAW_OT_clear_script(Operator):
#     """Clear the script input"""

#     bl_idname = "mindraw.clear_script"
#     bl_label = "Clear Script"

#     def execute(self, context: bpy.types.Context) -> set[str]:
#         context.scene.mindraw_props.script_code = ""
#         return {"FINISHED"}


# class MINDDRAW_OT_clear_output(Operator):
#     """Clear the output"""

#     bl_idname = "mindraw.clear_output"
#     bl_label = "Clear Output"

#     def execute(self, context: bpy.types.Context) -> set[str]:
#         context.scene.mindraw_props.output_text = "Output will appear here..."
#         return {"FINISHED"}


# class MINDDRAW_OT_get_view_context(Operator):
#     """Get current view context as text"""

#     bl_idname = "mindraw.get_view_context"
#     bl_label = "Get View Context"

#     def execute(self, context: bpy.types.Context) -> set[str]:
#         props: MindDrawProperties = context.scene.mindraw_props

#         # Collect view context information
#         context_info: List[str] = []

#         # Scene information
#         context_info.append(f"Scene: {context.scene.name}")
#         context_info.append(f"Objects in scene: {len(context.scene.objects)}")

#         # Current mode
#         context_info.append(f"Current mode: {context.mode}")

#         # Selected objects
#         selected_objects = [obj.name for obj in context.selected_objects]
#         if selected_objects:
#             context_info.append(f"Selected objects: {', '.join(selected_objects)}")
#         else:
#             context_info.append("No objects selected")

#         # Visible objects in viewport (simplified - first 10)
#         visible_objects: List[str] = []
#         for obj in context.scene.objects:
#             if obj.visible_get() and len(visible_objects) < 10:
#                 visible_objects.append(f"{obj.name} ({obj.type})")

#         if visible_objects:
#             context_info.append(f"Visible objects: {', '.join(visible_objects)}")

#         # Active object details
#         if context.active_object:
#             obj = context.active_object
#             context_info.append(f"Active object: {obj.name} ({obj.type})")
#             context_info.append(
#                 f"  Location: ({obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f})"
#             )
#             context_info.append(
#                 f"  Rotation: ({obj.rotation_euler.x:.2f}, {obj.rotation_euler.y:.2f}, {obj.rotation_euler.z:.2f})"
#             )
#             context_info.append(
#                 f"  Scale: ({obj.scale.x:.2f}, {obj.scale.y:.2f}, {obj.scale.z:.2f})"
#             )

#             # Detailed Armature information
#             if obj.type == "ARMATURE":
#                 context_info.extend(self._get_armature_details(obj))

#         # Camera information
#         if context.scene.camera:
#             cam = context.scene.camera
#             context_info.append(f"Active camera: {cam.name}")
#             context_info.append(
#                 f"  Camera location: ({cam.location.x:.2f}, {cam.location.y:.2f}, {cam.location.z:.2f})"
#             )

#         # Join all information
#         context_text = "\n".join(context_info)
#         props.output_text = context_text

#         self.report({"INFO"}, "View context captured")
#         return {"FINISHED"}

#     def _get_armature_details(self, armature_obj: bpy.types.Object) -> List[str]:
#         """Get detailed information about armature bones and hierarchy"""
#         details: List[str] = []
#         details.append("")
#         details.append("  Armature Details:")
#         details.append(f"    Total bones: {len(armature_obj.data.bones)}")

#         if not armature_obj.data.bones:
#             details.append("    No bones found")
#             return details

#         # Get root bones (bones with no parent)
#         root_bones = [bone for bone in armature_obj.data.bones if not bone.parent]

#         details.append("    Bone Hierarchy:")
#         for root_bone in root_bones:
#             details.extend(
#                 self._get_bone_hierarchy_info(root_bone, armature_obj, "      ├── ")
#             )

#         # Bone summary statistics
#         details.append("")
#         details.append("    Bone Summary:")
#         connected_count = sum(1 for bone in armature_obj.data.bones if bone.use_connect)
#         details.append(
#             f"      Connected bones: {connected_count}/{len(armature_obj.data.bones)}"
#         )

#         # Bone layers information
#         if hasattr(armature_obj.data, "layers"):
#             active_layers = [
#                 i for i, layer in enumerate(armature_obj.data.layers) if layer
#             ]
#             if active_layers:
#                 details.append(f"      Active layers: {active_layers}")

#         return details

#     def _get_bone_hierarchy_info(
#         self, bone: bpy.types.Bone, armature_obj: bpy.types.Object, prefix: str
#     ) -> List[str]:
#         """Get recursive bone hierarchy information"""
#         info: List[str] = []

#         # Bone basic info
#         bone_name = bone.name
#         parent_name = bone.parent.name if bone.parent else "ROOT"
#         connected = "CONNECTED" if bone.use_connect else "DISCONNECTED"

#         # Get bone world positions
#         head_pos = armature_obj.matrix_world @ bone.head
#         tail_pos = armature_obj.matrix_world @ bone.tail
#         bone_length = bone.length

#         info.append(f"{prefix}{bone_name} ({connected})")
#         info.append(
#             f"{prefix.replace('├──', '│  ').replace('└──', '   ')}  Parent: {parent_name}"
#         )
#         info.append(
#             f"{prefix.replace('├──', '│  ').replace('└──', '   ')}  Length: {bone_length:.3f}"
#         )
#         info.append(
#             f"{prefix.replace('├──', '│ ').replace('└──', '   ')}  Head: ({head_pos.x:.2f}, {head_pos.y:.2f}, {head_pos.z:.2f})"
#         )
#         info.append(
#             f"{prefix.replace('├──', '│ ').replace('└──', '   ')}  Tail: ({tail_pos.x:.2f}, {tail_pos.y:.2f}, {tail_pos.z:.2f})"
#         )

#         # Bone rotation in Euler angles
#         if bone.matrix:
#             euler = bone.matrix.to_euler()
#             info.append(
#                 f"{prefix.replace('├──', '│ ').replace('└──', '   ')}  Rotation: ({euler.x:.2f}, {euler.y:.2f}, {euler.z:.2f})"
#             )

#         # Get children
#         children = [child for child in armature_obj.data.bones if child.parent == bone]

#         if children:
#             for i, child in enumerate(children):
#                 is_last = i == len(children) - 1
#                 child_prefix = prefix.replace("├──", "│  ").replace("└──", "   ")
#                 if is_last:
#                     child_prefix += "└── "
#                 else:
#                     child_prefix += "├── "

#                 info.extend(
#                     self._get_bone_hierarchy_info(child, armature_obj, child_prefix)
#                 )

#         return info


# class MINDDRAW_OT_copy_to_clipboard(Operator):
#     """Copy output text to clipboard"""

#     bl_idname = "mindraw.copy_to_clipboard"
#     bl_label = "Copy to Clipboard"

#     def execute(self, context):
#         props = context.scene.mindraw_props

#         # Copy to clipboard using Blender's clipboard
#         context.window_manager.clipboard = props.output_text

#         self.report({"INFO"}, "Output copied to clipboard")
#         return {"FINISHED"}


# class MINDDRAW_OT_create_filedir(Operator):
#     """Create input.txt and output.txt in FileTalk directory"""

#     bl_idname = "mindraw.create_filedir"
#     bl_label = "Create Files"

#     def execute(self, context):
#         props = context.scene.mindraw_props

#         if not props.filetalk_directory.strip():
#             self.report({"ERROR"}, "Please set FileTalk directory first")
#             return {"CANCELLED"}

#         directory = props.filetalk_directory

#         try:
#             # Create directory if it doesn't exist
#             os.makedirs(directory, exist_ok=True)

#             # Create input.txt
#             input_path = os.path.join(directory, "input.txt")
#             with open(input_path, "w") as f:
#                 f.write(
#                     "# Enter your Python code here\nprint('Hello from FileTalk!')\n\n# Example: Create a cube\n# bpy.ops.mesh.primitive_cube_add()"
#                 )

#             # Create output.txt
#             output_path = os.path.join(directory, "output.txt")
#             with open(output_path, "w") as f:
#                 f.write("Output will appear here...")

#             self.report({"INFO"}, f"Files created in {directory}")
#             return {"FINISHED"}

#         except Exception as e:
#             self.report({"ERROR"}, f"Failed to create files: {str(e)}")
#             return {"CANCELLED"}


# class MINDDRAW_OT_filedir_talk(Operator):
#     """Read input.txt, execute code, save to output.txt"""

#     bl_idname = "mindraw.filedir_talk"
#     bl_label = "FileTalk"

#     def execute(self, context):
#         props = context.scene.mindraw_props

#         if not props.filetalk_directory.strip():
#             self.report({"ERROR"}, "Please set FileTalk directory first")
#             return {"CANCELLED"}

#         directory = props.filetalk_directory
#         input_path = os.path.join(directory, "input.txt")
#         output_path = os.path.join(directory, "output.txt")

#         try:
#             # Check if input.txt exists
#             if not os.path.exists(input_path):
#                 self.report(
#                     {"ERROR"}, "input.txt not found. Please create files first."
#                 )
#                 return {"CANCELLED"}

#             # Read code from input.txt
#             with open(input_path, "r") as f:
#                 script_code = f.read()

#             if not script_code.strip():
#                 self.report({"WARNING"}, "input.txt is empty")
#                 return {"CANCELLED"}

#             # Capture stdout
#             old_stdout = sys.stdout
#             sys.stdout = captured_output = io.StringIO()

#             try:
#                 # Execute the script with Blender context
#                 exec_context = {
#                     "bpy": bpy,
#                     "context": context,
#                     "C": context,
#                 }

#                 exec(script_code, exec_context)

#                 # Get the output
#                 output = captured_output.getvalue()
#                 if output:
#                     result_text = output
#                 else:
#                     result_text = "Script executed successfully (no output)"

#                 # Save to output.txt
#                 with open(output_path, "w") as f:
#                     f.write(result_text)

#                 self.report({"INFO"}, "FileTalk completed successfully")

#             except Exception as e:
#                 error_msg = f"Error: {str(e)}"

#                 # Save error to output.txt
#                 with open(output_path, "w") as f:
#                     f.write(error_msg)

#                 self.report({"ERROR"}, f"FileTalk failed: {str(e)}")

#             finally:
#                 # Restore stdout
#                 sys.stdout = old_stdout

#             return {"FINISHED"}

#         except Exception as e:
#             self.report({"ERROR"}, f"FileTalk failed: {str(e)}")
#             return {"CANCELLED"}


# class MINDDRAW_OT_select_json_file(Operator, ImportHelper):
#     """Select JSON file for import/export"""

#     bl_idname = "mindraw.select_json_file"
#     bl_label = "Select JSON File"
#     bl_options = {"REGISTER", "UNDO"}

#     filename_ext = ".json"
#     filter_glob: StringProperty(
#         default="*.json",
#         options={"HIDDEN"},
#         maxlen=255,
#     )

#     def execute(self, context):
#         props = context.scene.mindraw_props
#         props.json_file_path = self.filepath
#         self.report({"INFO"}, f"JSON file selected: {self.filepath}")
#         return {"FINISHED"}


# class MINDDRAW_OT_draw_from_json(Operator):
#     """Draw Grease Pencil strokes from JSON file"""

#     bl_idname = "mindraw.draw_from_json"
#     bl_label = "Draw from JSON"
#     bl_options = {"REGISTER", "UNDO"}

#     def execute(self, context):
#         props = context.scene.mindraw_props

#         if not props.json_file_path.strip():
#             self.report({"WARNING"}, "Please select a JSON file first")
#             return {"CANCELLED"}

#         # Check if we're in Grease Pencil Draw mode
#         if context.mode != "PAINT_GREASE_PENCIL":
#             self.report({"WARNING"}, "Only works in Grease Pencil Draw mode")
#             return {"CANCELLED"}

#         # Check if we have access to Grease Pencil
#         gp = bpy.context.grease_pencil
#         if not gp:
#             # Try to create a new Grease Pencil object
#             try:
#                 bpy.ops.grease_pencil.add()
#                 gp = bpy.context.grease_pencil
#                 if not gp:
#                     self.report({"ERROR"}, "Failed to create Grease Pencil object")
#                     return {"CANCELLED"}
#                 self.report({"INFO"}, "Created new Grease Pencil object")
#             except Exception as e:
#                 self.report({"ERROR"}, f"Failed to create Grease Pencil: {str(e)}")
#                 return {"CANCELLED"}

#         try:
#             # Read JSON file
#             with open(props.json_file_path, 'r') as f:
#                 json_data = json.load(f)

#             # Get image data
#             image_data = json_data.get("image_data", {})
#             layers = image_data.get("layers", [])

#             if not layers:
#                 self.report({"WARNING"}, "No layers found in JSON file")
#                 return {"CANCELLED"}

#             # Use bpy.context.grease_pencil for stable access
#             gp = bpy.context.grease_pencil

#             # Process each layer
#             for layer_data in layers:
#                 layer_name = layer_data.get("name", "Unknown Layer")
#                 strokes = layer_data.get("strokes", [])

#                 # Create new layer
#                 bpy.ops.grease_pencil.layer_add()
#                 new_layer = bpy.context.grease_pencil.layers.active
#                 new_layer.name = layer_name

#                 # Get the first frame
#                 if not new_layer.frames:
#                     new_layer.frames.new(frame_number=1)
#                 frame = new_layer.frames[0]
#                 drawing = frame.drawing

#                 # Process each stroke
#                 for stroke_data in strokes:
#                     points = stroke_data.get("points", [])
#                     if not points:
#                         continue

#                     # Create stroke
#                     drawing.add_strokes([len(points)])
#                     stroke = drawing.strokes[-1]

#                     # Set point positions (direct coordinate mapping)
#                     for i, point_data in enumerate(points):
#                         x = point_data.get("x", 0.0)
#                         z = point_data.get("z", 0.0)
#                         y = 0.0  # X-Z plane, so Y is 0
#                         stroke.points[i].position = (x, y, z)

#             self.report({"INFO"}, f"Successfully drew {len(layers)} layers from JSON")
#             return {"FINISHED"}

#         except Exception as e:
#             self.report({"ERROR"}, f"Failed to draw from JSON: {str(e)}")
#             return {"CANCELLED"}


# class MINDDRAW_OT_sync_to_json(Operator):
#     """Sync Grease Pencil data to JSON file"""

#     bl_idname = "mindraw.sync_to_json"
#     bl_label = "Sync to JSON"
#     bl_options = {"REGISTER", "UNDO"}

#     def execute(self, context):
#         props = context.scene.mindraw_props

#         if not props.json_file_path.strip():
#             self.report({"WARNING"}, "Please select a JSON file first")
#             return {"CANCELLED"}

#         # Check if we're in Grease Pencil Draw mode
#         if context.mode != "PAINT_GREASE_PENCIL":
#             self.report({"WARNING"}, "Only works in Grease Pencil Draw mode")
#             return {"CANCELLED"}

#         # Check if we have access to Grease Pencil
#         gp = bpy.context.grease_pencil
#         if not gp:
#             # Try to create a new Grease Pencil object
#             try:
#                 bpy.ops.grease_pencil.add()
#                 gp = bpy.context.grease_pencil
#                 if not gp:
#                     self.report({"ERROR"}, "Failed to create Grease Pencil object")
#                     return {"CANCELLED"}
#                 self.report({"INFO"}, "Created new Grease Pencil object")
#             except Exception as e:
#                 self.report({"ERROR"}, f"Failed to create Grease Pencil: {str(e)}")
#                 return {"CANCELLED"}

#         try:
#             # Use bpy.context.grease_pencil for stable access
#             gp = bpy.context.grease_pencil

#             # Prepare JSON structure
#             json_data = {
#                 "image_data": {
#                     "description": "Simplified storyboard sketch data, grouped by objects with color mapping.",
#                     "layers": []
#                 }
#             }

#             # Process each layer
#             for layer in gp.layers:
#                 layer_data = {
#                     "name": layer.name,
#                     "color": {"r": 0, "g": 0, "b": 0},  # Default black color
#                     "description": f"Layer {layer.name}",
#                     "strokes": []
#                 }

#                 # Process each frame (use first frame)
#                 if layer.frames:
#                     frame = layer.frames[0]
#                     drawing = frame.drawing

#                     # Process each stroke
#                     for i, stroke in enumerate(drawing.strokes):
#                         stroke_data = {
#                             "id": i + 1,
#                             "label": f"stroke_{i + 1}",
#                             "type": "line",  # Default to line type
#                             "points": []
#                         }

#                         # Extract points (direct coordinate mapping)
#                         for point in stroke.points:
#                             point_data = {
#                                 "x": round(point.position.x, 1),
#                                 "z": round(point.position.z, 1)
#                             }
#                             stroke_data["points"].append(point_data)

#                         layer_data["strokes"].append(stroke_data)

#                 json_data["image_data"]["layers"].append(layer_data)

#             # Write to JSON file
#             with open(props.json_file_path, 'w') as f:
#                 json.dump(json_data, f, indent=2)

#             self.report({"INFO"}, f"Successfully synced {len(gp.layers)} layers to JSON")
#             return {"FINISHED"}

#         except Exception as e:
#             self.report({"ERROR"}, f"Failed to sync to JSON: {str(e)}")
#             return {"CANCELLED"}


# class MINDDRAW_OT_create_circle_stroke(Operator):
#     """Create a circle stroke on selected Grease Pencil layer"""

#     bl_idname = "mindraw.create_circle_stroke"
#     bl_label = "Create Circle"
#     bl_options = {"REGISTER", "UNDO"}

#     def execute(self, context):
#         # Check if we're in Grease Pencil Draw mode
#         if context.mode != "PAINT_GREASE_PENCIL":
#             self.report({"WARNING"}, "Only works in Grease Pencil Draw mode")
#             return {"CANCELLED"}

#         # Check if we have access to Grease Pencil
#         gp = bpy.context.grease_pencil
#         if not gp:
#             # Try to create a new Grease Pencil object
#             try:
#                 bpy.ops.grease_pencil.add()
#                 gp = bpy.context.grease_pencil
#                 if not gp:
#                     self.report({"ERROR"}, "Failed to create Grease Pencil object")
#                     return {"CANCELLED"}
#                 self.report({"INFO"}, "Created new Grease Pencil object")
#             except Exception as e:
#                 self.report({"ERROR"}, f"Failed to create Grease Pencil: {str(e)}")
#                 return {"CANCELLED"}

#         try:
#             # Use bpy.context.grease_pencil for stable access
#             gp = bpy.context.grease_pencil

#             # Get active layer
#             active_layer = gp.layers.active
#             if not active_layer:
#                 self.report({"WARNING"}, "No active Grease Pencil layer")
#                 return {"CANCELLED"}

#             # Use the first frame (simplest and most reliable approach)
#             frame = active_layer.frames[0]

#             # Get drawing
#             drawing = frame.drawing

#             # Create new stroke with 33 points (32 segments + 1 to close circle)
#             drawing.add_strokes([33])
#             stroke = drawing.strokes[-1]

#             # Generate circle points (32 segments to make a smooth circle)
#             radius = 1.0
#             segments = 32

#             for i in range(segments + 1):  # +1 to close the circle
#                 angle = 2 * math.pi * i / segments
#                 x = radius * math.cos(angle)
#                 y = 0.0  # Fixed Y coordinate for X-Z plane
#                 z = radius * math.sin(angle)  # Use Z for the circular motion

#                 # Set point properties directly (only position is available in Blender 5.0)
#                 stroke.points[i].position = (x, y, z)

#             self.report({"INFO"}, "Circle stroke created successfully")
#             return {"FINISHED"}

#         except Exception as e:
#             self.report({"ERROR"}, f"Failed to create circle stroke: {str(e)}")
#             return {"CANCELLED"}


# class MINDDRAW_PT_script_panel(Panel):
#     """Main panel for Python script execution"""

#     bl_label = "MindDraw Panel"
#     bl_idname = "MINDDRAW_PT_script_panel"
#     bl_space_type = "VIEW_3D"
#     bl_region_type = "UI"
#     bl_category = "MindDraw"

#     def draw(self, context: bpy.types.Context) -> None:
#         layout = self.layout
#         props: MindDrawProperties = context.scene.mindraw_props

#         # Title
#         box = layout.box()
#         box.label(text="Python Script Executor")
#         box.label(text="Execute Python code in Blender")

#         # Status Information
#         layout.separator()
#         status_box = layout.box()
#         status_box.label(text="Current Status")

#         # Active Window Information
#         if context.window:
#             status_box.label(
#                 text=f"Active Window: {context.window.width}x{context.window.height}"
#             )

#         # Current Interactive Mode
#         current_mode = context.mode
#         mode_display = current_mode.replace("_", " ").title()
#         status_box.label(text=f"Current Mode: {mode_display}")

#         # Area Type Information
#         if context.area:
#             area_type = context.area.type
#             status_box.label(text=f"Area Type: {area_type}")

#         # Screen Information
#         if context.screen:
#             status_box.label(text=f"Screen: {context.screen.name}")

#         # Debug information
#         status_box.separator()
#         status_box.label(text="Debug Info:")
#         status_box.label(text=f"  Mode: '{context.mode}'")
#         status_box.label(
#             text=f"  Active Object: {context.active_object.name if context.active_object else 'None'}"
#         )
#         if context.active_object:
#             status_box.label(text=f"  Object Type: {context.active_object.type}")

#         # Edit Mode Object Information (only show in Edit mode)
#         is_edit_mode = context.mode.startswith("EDIT_")
#         status_box.label(text=f"  Is Edit Mode: {is_edit_mode}")

#         if is_edit_mode and context.active_object:
#             obj = context.active_object
#             status_box.separator()
#             status_box.label(text="Edit Mode Object Info:")
#             status_box.label(text=f"  Object: {obj.name} ({obj.type})")

#             # Object transform info
#             status_box.label(
#                 text=f"  Location: ({obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f})"
#             )

#             # Edit mode specific information
#             try:
#                 if hasattr(obj.data, "total_verts"):
#                     status_box.label(text=f"  Vertices: {obj.data.total_verts}")
#                 if hasattr(obj.data, "total_edges"):
#                     status_box.label(text=f"  Edges: {obj.data.total_edges}")
#                 if hasattr(obj.data, "total_polygons"):
#                     status_box.label(text=f"  Faces: {obj.data.total_polygons}")
#             except Exception as e:
#                 status_box.label(text=f"  Data Error: {str(e)}")

#             # Selection mode info
#             try:
#                 if obj.type == "GREASEPENCIL":
#                     # Grease Pencil selection mode
#                     if hasattr(context.tool_settings, "gpencil_select_mode"):
#                         gp_mode = context.tool_settings.gpencil_select_mode
#                         mode_map = {0: "POINT", 1: "STROKE", 2: "SEGMENT"}
#                         mode_text = mode_map.get(gp_mode, "UNKNOWN")
#                         status_box.label(text=f"  GPencil Select Mode: {mode_text}")
#                 elif hasattr(context.tool_settings, "mesh_select_mode"):
#                     # Mesh selection mode
#                     select_mode = context.tool_settings.mesh_select_mode
#                     mode_text = []
#                     if select_mode[0]:
#                         mode_text.append("Vertex")
#                     if select_mode[1]:
#                         mode_text.append("Edge")
#                     if select_mode[2]:
#                         mode_text.append("Face")
#                     if mode_text:
#                         status_box.label(text=f"  Select Mode: {', '.join(mode_text)}")
#             except Exception as e:
#                 status_box.label(text=f"  Select Mode Error: {str(e)}")

#             # Selected points information
#             try:
#                 if obj.type == "GREASEPENCIL":
#                     # Grease Pencil selection information
#                     selected_points = []
#                     selected_strokes = []

#                     # Use bpy.context.grease_pencil for stable access
#                     gp = bpy.context.grease_pencil

#                     # Get active layer object (layers.active returns GreasePencilLayer object directly)
#                     try:
#                         active_layer = (
#                             gp.layers.active if hasattr(gp, "layers") else None
#                         )
#                         active_layer_name = (
#                             active_layer.name if active_layer else "Unknown"
#                         )
#                     except:
#                         active_layer = None
#                         active_layer_name = "Unknown"

#                     # Process the active layer
#                     if active_layer:
#                         for frame in active_layer.frames:
#                             drawing = frame.drawing
#                             if hasattr(drawing, "strokes"):
#                                 for stroke in drawing.strokes:
#                                     if stroke.select:
#                                         selected_strokes.append(stroke)
#                                     for point in stroke.points:
#                                         if point.select:
#                                             selected_points.append(point)

#                     status_box.label(text=f"  Active Layer: {active_layer_name}")
#                     status_box.label(text=f"  Selected Points: {len(selected_points)}")
#                     status_box.label(
#                         text=f"  Selected Strokes: {len(selected_strokes)}"
#                     )

#                     # Show detailed info for first 3 selected points
#                     for i, point in enumerate(selected_points[:3]):
#                         world_pos = obj.matrix_world @ point.position
#                         status_box.label(
#                             text=f"    P{i}: ({point.position.x:.2f}, {point.position.y:.2f}, {point.position.z:.2f})"
#                         )

#                     if len(selected_points) > 3:
#                         status_box.label(
#                             text=f"    ... and {len(selected_points) - 3} more"
#                         )

#                     # Show detailed info for first 2 selected strokes
#                     for i, stroke in enumerate(selected_strokes[:2]):
#                         status_box.label(
#                             text=f"    Stroke {i}: {len(stroke.points)} points"
#                         )

#                     if len(selected_strokes) > 2:
#                         status_box.label(
#                             text=f"    ... and {len(selected_strokes) - 2} more"
#                         )

#                 elif hasattr(obj.data, "vertices"):
#                     # Mesh selection information
#                     selected_vertices = [v for v in obj.data.vertices if v.select]
#                     status_box.label(
#                         text=f"  Selected Vertices: {len(selected_vertices)}"
#                     )

#                     # Show detailed info for first 5 selected vertices
#                     for i, vertex in enumerate(selected_vertices[:5]):
#                         world_pos = obj.matrix_world @ vertex.co
#                         status_box.label(
#                             text=f"    V{vertex.index}: ({vertex.co.x:.2f}, {vertex.co.y:.2f}, {vertex.co.z:.2f})"
#                         )

#                     if len(selected_vertices) > 5:
#                         status_box.label(
#                             text=f"    ... and {len(selected_vertices) - 5} more"
#                         )

#                 if hasattr(obj.data, "edges"):
#                     selected_edges = [e for e in obj.data.edges if e.select]
#                     status_box.label(text=f"  Selected Edges: {len(selected_edges)}")

#                     # Show detailed info for first 3 selected edges
#                     for i, edge in enumerate(selected_edges[:3]):
#                         status_box.label(
#                             text=f"    E{edge.index}: vertices {edge.vertices[0]}-{edge.vertices[1]}"
#                         )

#                     if len(selected_edges) > 3:
#                         status_box.label(
#                             text=f"    ... and {len(selected_edges) - 3} more"
#                         )

#                 if hasattr(obj.data, "polygons"):
#                     selected_faces = [f for f in obj.data.polygons if f.select]
#                     status_box.label(text=f"  Selected Faces: {len(selected_faces)}")

#                     # Show detailed info for first 3 selected faces
#                     for i, face in enumerate(selected_faces[:3]):
#                         verts_str = "-".join(
#                             str(v) for v in face.vertices[:4]
#                         )  # Show first 4 vertices
#                         if len(face.vertices) > 4:
#                             verts_str += "..."
#                         status_box.label(
#                             text=f"    F{face.index}: vertices {verts_str}"
#                         )

#                     if len(selected_faces) > 3:
#                         status_box.label(
#                             text=f"    ... and {len(selected_faces) - 3} more"
#                         )

#             except Exception as e:
#                 status_box.label(text=f"  Selection Error: {str(e)}")

#         # Script input area
#         layout.separator()
#         layout.label(text="Script Input:")
#         script_box = layout.box()
#         script_box.scale_y = 0.8
#         script_box.prop(props, "script_code", text="")

#         # Buttons
#         layout.separator()
#         row = layout.row(align=True)
#         row.operator("mindraw.execute_script")
#         row.operator("mindraw.clear_script")
#         row.operator("mindraw.clear_output")

#         # View context buttons
#         layout.separator()
#         row = layout.row(align=True)
#         row.operator("mindraw.get_view_context")
#         row.operator("mindraw.copy_to_clipboard")

#         # Grease Pencil Draw mode buttons (only show in Draw mode)
#         if context.mode == "PAINT_GREASE_PENCIL":
#             layout.separator()
#             row = layout.row(align=True)
#             row.operator("mindraw.create_circle_stroke")

#         # JSON Import/Export section
#         layout.separator()
#         box = layout.box()
#         box.label(text="JSON Import/Export")
#         box.label(text="Grease Pencil data exchange")

#         layout.separator()
#         layout.label(text="JSON File:")
#         layout.prop(props, "json_file_path", text="")

#         layout.separator()
#         row = layout.row(align=True)
#         row.operator("mindraw.draw_from_json")
#         row.operator("mindraw.sync_to_json")

#         # FileTalk section
#         layout.separator()
#         box = layout.box()
#         box.label(text="FileTalk Communication")
#         box.label(text="File-based AI integration")

#         layout.separator()
#         layout.label(text="FileTalk Directory:")
#         layout.prop(props, "filetalk_directory", text="")

#         layout.separator()
#         row = layout.row(align=True)
#         row.operator("mindraw.create_filedir")
#         row.operator("mindraw.filedir_talk")

#         # Output area
#         layout.separator()
#         layout.label(text="Output:")
#         output_box = layout.box()
#         output_box.scale_y = 0.6
#         output_box.prop(props, "output_text", text="", emboss=False)


def register():
    global is_running, server_thread

    print("[MindDraw] Registering addon...")

    # Start socket server thread
    is_running = True
    server_thread = threading.Thread(target=socket_server_thread, daemon=True)
    server_thread.start()

    print("[MindDraw] Socket server started in background thread")


def unregister():
    global is_running, server_thread

    print("[MindDraw] Unregistering addon...")

    # Stop socket server
    is_running = False

    # Wait for thread to finish (with timeout)
    if server_thread and server_thread.is_alive():
        server_thread.join(timeout=2.0)
        if server_thread.is_alive():
            print("[MindDraw] Warning: Server thread did not stop gracefully")

    print("[MindDraw] Socket server stopped")


if __name__ == "__main__":
    register()
