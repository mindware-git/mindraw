import bpy
import sys
import io
import os
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import StringProperty

bl_info = {
    "name": "MindDraw Addon",
    "author": "Mindware",
    "version": (0, 0, 1),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > MindDraw",
    "description": "Python script executor for AI integration",
    "category": "Development",
}


class MindDrawProperties(PropertyGroup):
    """Properties to store script code and output"""

    script_code: StringProperty(
        name="Script Code",
        description="Enter Python code to execute",
        default="# Enter your Python code here\nprint('Hello from MindDraw!')\n\n# Example: Create a cube\n# bpy.ops.mesh.primitive_cube_add()",
        options={"TEXTEDIT_UPDATE"},
    )

    output_text: StringProperty(
        name="Output",
        description="Script execution output",
        default="Output will appear here...",
        options={"TEXTEDIT_UPDATE"},
    )

    filetalk_directory: StringProperty(
        name="FileTalk Directory",
        description="Directory for file-based communication",
        default="",
        subtype="DIR_PATH",
    )


class MINDDRAW_OT_execute_script(Operator):
    """Execute the Python script and show output"""

    bl_idname = "mindraw.execute_script"
    bl_label = "Execute Script"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.mindraw_props

        if not props.script_code.strip():
            self.report({"WARNING"}, "No script to execute")
            return {"CANCELLED"}

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            # Execute the script with Blender context
            exec_context = {
                "bpy": bpy,
                "context": context,
                "C": context,
            }

            exec(props.script_code, exec_context)

            # Get the output
            output = captured_output.getvalue()
            if output:
                props.output_text = output
            else:
                props.output_text = "Script executed successfully (no output)"

            self.report({"INFO"}, "Script executed successfully")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            props.output_text = error_msg
            self.report({"ERROR"}, error_msg)

        finally:
            # Restore stdout
            sys.stdout = old_stdout

        return {"FINISHED"}


class MINDDRAW_OT_clear_script(Operator):
    """Clear the script input"""

    bl_idname = "mindraw.clear_script"
    bl_label = "Clear Script"

    def execute(self, context):
        context.scene.mindraw_props.script_code = ""
        return {"FINISHED"}


class MINDDRAW_OT_clear_output(Operator):
    """Clear the output"""

    bl_idname = "mindraw.clear_output"
    bl_label = "Clear Output"

    def execute(self, context):
        context.scene.mindraw_props.output_text = "Output will appear here..."
        return {"FINISHED"}


class MINDDRAW_OT_get_view_context(Operator):
    """Get current view context as text"""

    bl_idname = "mindraw.get_view_context"
    bl_label = "Get View Context"

    def execute(self, context):
        props = context.scene.mindraw_props

        # Collect view context information
        context_info = []

        # Scene information
        context_info.append(f"Scene: {context.scene.name}")
        context_info.append(f"Objects in scene: {len(context.scene.objects)}")

        # Current mode
        context_info.append(f"Current mode: {context.mode}")

        # Selected objects
        selected_objects = [obj.name for obj in context.selected_objects]
        if selected_objects:
            context_info.append(f"Selected objects: {', '.join(selected_objects)}")
        else:
            context_info.append("No objects selected")

        # Visible objects in viewport (simplified - first 10)
        visible_objects = []
        for obj in context.scene.objects:
            if obj.visible_get() and len(visible_objects) < 10:
                visible_objects.append(f"{obj.name} ({obj.type})")

        if visible_objects:
            context_info.append(f"Visible objects: {', '.join(visible_objects)}")

        # Active object details
        if context.active_object:
            obj = context.active_object
            context_info.append(f"Active object: {obj.name} ({obj.type})")
            context_info.append(
                f"  Location: ({obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f})"
            )
            context_info.append(
                f"  Rotation: ({obj.rotation_euler.x:.2f}, {obj.rotation_euler.y:.2f}, {obj.rotation_euler.z:.2f})"
            )
            context_info.append(
                f"  Scale: ({obj.scale.x:.2f}, {obj.scale.y:.2f}, {obj.scale.z:.2f})"
            )

            # Detailed Armature information
            if obj.type == "ARMATURE":
                context_info.extend(self._get_armature_details(obj))

        # Camera information
        if context.scene.camera:
            cam = context.scene.camera
            context_info.append(f"Active camera: {cam.name}")
            context_info.append(
                f"  Camera location: ({cam.location.x:.2f}, {cam.location.y:.2f}, {cam.location.z:.2f})"
            )

        # Join all information
        context_text = "\n".join(context_info)
        props.output_text = context_text

        self.report({"INFO"}, "View context captured")
        return {"FINISHED"}

    def _get_armature_details(self, armature_obj):
        """Get detailed information about armature bones and hierarchy"""
        details = []
        details.append("")
        details.append("  Armature Details:")
        details.append(f"    Total bones: {len(armature_obj.data.bones)}")

        if not armature_obj.data.bones:
            details.append("    No bones found")
            return details

        # Get root bones (bones with no parent)
        root_bones = [bone for bone in armature_obj.data.bones if not bone.parent]

        details.append("    Bone Hierarchy:")
        for root_bone in root_bones:
            details.extend(
                self._get_bone_hierarchy_info(root_bone, armature_obj, "      ├── ")
            )

        # Bone summary statistics
        details.append("")
        details.append("    Bone Summary:")
        connected_count = sum(1 for bone in armature_obj.data.bones if bone.use_connect)
        details.append(
            f"      Connected bones: {connected_count}/{len(armature_obj.data.bones)}"
        )

        # Bone layers information
        if hasattr(armature_obj.data, "layers"):
            active_layers = [
                i for i, layer in enumerate(armature_obj.data.layers) if layer
            ]
            if active_layers:
                details.append(f"      Active layers: {active_layers}")

        return details

    def _get_bone_hierarchy_info(self, bone, armature_obj, prefix):
        """Get recursive bone hierarchy information"""
        info = []

        # Bone basic info
        bone_name = bone.name
        parent_name = bone.parent.name if bone.parent else "ROOT"
        connected = "CONNECTED" if bone.use_connect else "DISCONNECTED"

        # Get bone world positions
        head_pos = armature_obj.matrix_world @ bone.head
        tail_pos = armature_obj.matrix_world @ bone.tail
        bone_length = bone.length

        info.append(f"{prefix}{bone_name} ({connected})")
        info.append(
            f"{prefix.replace('├──', '│  ').replace('└──', '   ')}  Parent: {parent_name}"
        )
        info.append(
            f"{prefix.replace('├──', '│  ').replace('└──', '   ')}  Length: {bone_length:.3f}"
        )
        info.append(
            f"{prefix.replace('├──', '│ ').replace('└──', '   ')}  Head: ({head_pos.x:.2f}, {head_pos.y:.2f}, {head_pos.z:.2f})"
        )
        info.append(
            f"{prefix.replace('├──', '│ ').replace('└──', '   ')}  Tail: ({tail_pos.x:.2f}, {tail_pos.y:.2f}, {tail_pos.z:.2f})"
        )

        # Bone rotation in Euler angles
        if bone.matrix:
            euler = bone.matrix.to_euler()
            info.append(
                f"{prefix.replace('├──', '│ ').replace('└──', '   ')}  Rotation: ({euler.x:.2f}, {euler.y:.2f}, {euler.z:.2f})"
            )

        # Get children
        children = [child for child in armature_obj.data.bones if child.parent == bone]

        if children:
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                child_prefix = prefix.replace("├──", "│  ").replace("└──", "   ")
                if is_last:
                    child_prefix += "└── "
                else:
                    child_prefix += "├── "

                info.extend(
                    self._get_bone_hierarchy_info(child, armature_obj, child_prefix)
                )

        return info


class MINDDRAW_OT_copy_to_clipboard(Operator):
    """Copy output text to clipboard"""

    bl_idname = "mindraw.copy_to_clipboard"
    bl_label = "Copy to Clipboard"

    def execute(self, context):
        props = context.scene.mindraw_props

        # Copy to clipboard using Blender's clipboard
        context.window_manager.clipboard = props.output_text

        self.report({"INFO"}, "Output copied to clipboard")
        return {"FINISHED"}


class MINDDRAW_OT_create_filedir(Operator):
    """Create input.txt and output.txt in FileTalk directory"""

    bl_idname = "mindraw.create_filedir"
    bl_label = "Create Files"

    def execute(self, context):
        props = context.scene.mindraw_props

        if not props.filetalk_directory.strip():
            self.report({"ERROR"}, "Please set FileTalk directory first")
            return {"CANCELLED"}

        directory = props.filetalk_directory

        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)

            # Create input.txt
            input_path = os.path.join(directory, "input.txt")
            with open(input_path, "w") as f:
                f.write(
                    "# Enter your Python code here\nprint('Hello from FileTalk!')\n\n# Example: Create a cube\n# bpy.ops.mesh.primitive_cube_add()"
                )

            # Create output.txt
            output_path = os.path.join(directory, "output.txt")
            with open(output_path, "w") as f:
                f.write("Output will appear here...")

            self.report({"INFO"}, f"Files created in {directory}")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to create files: {str(e)}")
            return {"CANCELLED"}


class MINDDRAW_OT_filedir_talk(Operator):
    """Read input.txt, execute code, save to output.txt"""

    bl_idname = "mindraw.filedir_talk"
    bl_label = "FileTalk"

    def execute(self, context):
        props = context.scene.mindraw_props

        if not props.filetalk_directory.strip():
            self.report({"ERROR"}, "Please set FileTalk directory first")
            return {"CANCELLED"}

        directory = props.filetalk_directory
        input_path = os.path.join(directory, "input.txt")
        output_path = os.path.join(directory, "output.txt")

        try:
            # Check if input.txt exists
            if not os.path.exists(input_path):
                self.report(
                    {"ERROR"}, "input.txt not found. Please create files first."
                )
                return {"CANCELLED"}

            # Read code from input.txt
            with open(input_path, "r") as f:
                script_code = f.read()

            if not script_code.strip():
                self.report({"WARNING"}, "input.txt is empty")
                return {"CANCELLED"}

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()

            try:
                # Execute the script with Blender context
                exec_context = {
                    "bpy": bpy,
                    "context": context,
                    "C": context,
                }

                exec(script_code, exec_context)

                # Get the output
                output = captured_output.getvalue()
                if output:
                    result_text = output
                else:
                    result_text = "Script executed successfully (no output)"

                # Save to output.txt
                with open(output_path, "w") as f:
                    f.write(result_text)

                self.report({"INFO"}, "FileTalk completed successfully")

            except Exception as e:
                error_msg = f"Error: {str(e)}"

                # Save error to output.txt
                with open(output_path, "w") as f:
                    f.write(error_msg)

                self.report({"ERROR"}, f"FileTalk failed: {str(e)}")

            finally:
                # Restore stdout
                sys.stdout = old_stdout

            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"FileTalk failed: {str(e)}")
            return {"CANCELLED"}


class MINDDRAW_PT_script_panel(Panel):
    """Main panel for Python script execution"""

    bl_label = "MindDraw Script Executor"
    bl_idname = "MINDDRAW_PT_script_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MindDraw"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mindraw_props

        # Title
        box = layout.box()
        box.label(text="Python Script Executor", icon="SCRIPT")
        box.label(text="Execute Python code in Blender", icon="INFO")

        # Script input area
        layout.separator()
        layout.label(text="Script Input:", icon="TEXT")
        script_box = layout.box()
        script_box.scale_y = 0.8
        script_box.prop(props, "script_code", text="")

        # Buttons
        layout.separator()
        row = layout.row(align=True)
        row.operator("mindraw.execute_script", icon="PLAY")
        row.operator("mindraw.clear_script", icon="TRASH")
        row.operator("mindraw.clear_output", icon="X")

        # View context buttons
        layout.separator()
        row = layout.row(align=True)
        row.operator("mindraw.get_view_context", icon="VIEWZOOM")
        row.operator("mindraw.copy_to_clipboard", icon="COPYDOWN")

        # FileTalk section
        layout.separator()
        box = layout.box()
        box.label(text="FileTalk Communication", icon="FILE_FOLDER")
        box.label(text="File-based AI integration", icon="INFO")

        layout.separator()
        layout.label(text="FileTalk Directory:", icon="FILE_FOLDER")
        layout.prop(props, "filetalk_directory", text="")

        layout.separator()
        row = layout.row(align=True)
        row.operator("mindraw.create_filedir", icon="FILE_NEW")
        row.operator("mindraw.filedir_talk", icon="MODIFIER")

        # Output area
        layout.separator()
        layout.label(text="Output:", icon="CONSOLE")
        output_box = layout.box()
        output_box.scale_y = 0.6
        output_box.prop(props, "output_text", text="", emboss=False)


def register():
    print("Hello MindDraw")
    bpy.utils.register_class(MindDrawProperties)
    bpy.utils.register_class(MINDDRAW_OT_execute_script)
    bpy.utils.register_class(MINDDRAW_OT_clear_script)
    bpy.utils.register_class(MINDDRAW_OT_clear_output)
    bpy.utils.register_class(MINDDRAW_OT_get_view_context)
    bpy.utils.register_class(MINDDRAW_OT_copy_to_clipboard)
    bpy.utils.register_class(MINDDRAW_OT_create_filedir)
    bpy.utils.register_class(MINDDRAW_OT_filedir_talk)
    bpy.utils.register_class(MINDDRAW_PT_script_panel)

    # Register properties to scene
    bpy.types.Scene.mindraw_props = bpy.props.PointerProperty(type=MindDrawProperties)


def unregister():
    print("Bye MindDraw")
    del bpy.types.Scene.mindraw_props
    bpy.utils.unregister_class(MINDDRAW_PT_script_panel)
    bpy.utils.unregister_class(MINDDRAW_OT_filedir_talk)
    bpy.utils.unregister_class(MINDDRAW_OT_create_filedir)
    bpy.utils.unregister_class(MINDDRAW_OT_copy_to_clipboard)
    bpy.utils.unregister_class(MINDDRAW_OT_get_view_context)
    bpy.utils.unregister_class(MINDDRAW_OT_clear_output)
    bpy.utils.unregister_class(MINDDRAW_OT_clear_script)
    bpy.utils.unregister_class(MINDDRAW_OT_execute_script)
    bpy.utils.unregister_class(MindDrawProperties)


if __name__ == "__main__":
    register()
