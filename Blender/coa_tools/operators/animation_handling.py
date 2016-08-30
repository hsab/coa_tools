'''
Copyright (C) 2015 Andreas Esau
andreasesau@gmail.com

Created by Andreas Esau

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import bpy
import bpy_extras
import bpy_extras.view3d_utils
from math import radians
import mathutils
from mathutils import Vector, Matrix, Quaternion
import math
import bmesh
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty
import os
from bpy_extras.io_utils import ExportHelper, ImportHelper
import json
from bpy.app.handlers import persistent
from .. functions import *

class AddKeyframe(bpy.types.Operator):
    bl_idname = "my_operator.add_keyframe"
    bl_label = "Add Keyframe"
    bl_description = "Add Keyframe"
    bl_options = {"REGISTER"}
    
    prop_name = StringProperty()
    add_keyframe = BoolProperty(default=True)
    interpolation = EnumProperty(default="BEZIER",items=(("BEZIER","BEZIER","BEZIER","IPO_BEZIER",0),("LINEAR","LINEAR","LINEAR","IPO_LINEAR",1),("CONSTANT","CONSTANT","CONSTANT","IPO_CONSTANT",2)))
    default_interpolation = StringProperty()
    
    @classmethod
    def poll(cls, context):
        return True

    def draw(self,context):
        layout = self.layout
        row = layout.row()
        row.prop(self,"interpolation",expand=True)
    
    def create_keyframe(self,context,event,data_path,group=""):
        sprite = context.active_object
        sprite_object = get_sprite_object(sprite)
        
        if sprite_object.coa_anim_collections_index > 1:
            if self.add_keyframe:
                for sprite in context.selected_objects:
                    if sprite.animation_data != None and sprite.animation_data.action != None:
                        if group != "":
                            sprite.keyframe_insert(data_path,group=group)
                        else:
                            sprite.keyframe_insert(data_path)    
                        
                        for fcurve in sprite.animation_data.action.fcurves:
                            if data_path in fcurve.data_path:
                                for key in fcurve.keyframe_points:
                                    if key.co[0] == context.scene.frame_current:
                                        if event == None:
                                            key.interpolation = self.interpolation
                                        else:
                                            key.interpolation = self.default_interpolation    
                    else:
                        create_action(context,obj=sprite)
                        if group != "":
                            sprite.keyframe_insert(data_path,group=group)
                        else:
                            sprite.keyframe_insert(data_path)   
                self.report({'INFO'},str("Keyframe added at frame "+str(context.scene.frame_current)+"."))    
            else:
                for sprite in context.selected_objects:
                    if sprite.animation_data != None and sprite.animation_data.action != None:
                        sprite.keyframe_delete(data_path)
                        
                        collection = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index]
                        action_name = collection.name + "_" +sprite.name
                        if action_name in bpy.data.actions:
                            action = bpy.data.actions[action_name]
                            if len(action.fcurves) == 0:
                                action.use_fake_user = False
                                action.user_clear()   
                        self.report({'INFO'},str("Keyframe deleted at frame "+str(context.scene.frame_current)+"."))
                        set_action(context)
                    else:
                        self.report({'WARNING'},str("Sprite has no Animation assigned."))
        else:
            self.report({'WARNING'},str("No Animation selected"))
    
    
    def create_bone_keyframe(self,context,event,prop_name):
        obj = context.active_object
        if obj != None and obj.type == "ARMATURE" and obj.mode == "POSE":
            for pose_bone in context.selected_pose_bones:
                data_path = 'pose.bones["'+str(pose_bone.name)+'"].'+prop_name
                
                if pose_bone.rotation_mode == "QUATERNION" and prop_name == "rotation":
                    data_path = data_path.replace(".rotation",".rotation_quaternion")
                else:
                    data_path = data_path.replace(".rotation",".rotation_euler")
                    
                self.create_keyframe(context,event,data_path,group=pose_bone.name)     
    
    def invoke(self,context,event):
        wm = context.window_manager
        if event.ctrl:
            return wm.invoke_props_dialog(self)
        else:
            if self.prop_name in ["location","rotation","scale","LocRotScale"]:
                if self.prop_name == "LocRotScale":
                    data_path = "location"
                    self.create_bone_keyframe(context,event,data_path)
                    
                    data_path = "rotation"
                    self.create_bone_keyframe(context,event,data_path)
                    
                    data_path = "scale"
                    self.create_bone_keyframe(context,event,data_path)
                else:
                    self.create_bone_keyframe(context,event,self.prop_name)
            else:
                self.create_keyframe(context,event,self.prop_name)
            return {"FINISHED"}
        
    def execute(self,context):
        event = None
        if self.prop_name in ["location","rotation","scale","LocRotScale"]:
            if self.prop_name == "LocRotScale":
                data_path = "location"
                self.create_bone_keyframe(context,event,data_path)
                
                data_path = "rotation"
                self.create_bone_keyframe(context,event,data_path)
                
                data_path = "scale"
                self.create_bone_keyframe(context,event,data_path)
            else:
                self.create_bone_keyframe(context,event,self.prop_name)
        else:
            self.create_keyframe(context,event,self.prop_name) 
        return {"FINISHED"}   

class AddAnimationCollection(bpy.types.Operator):
    bl_idname = "my_operator.add_animation_collection"
    bl_label = "Add Animation Collection"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True
    
    sprite_object = None
    
    def create_actions_collection(self,context):
        if self.sprite_object != None:
            if len(self.sprite_object.coa_anim_collections) == 0:
                item = self.sprite_object.coa_anim_collections.add()
                item.name = "NO ACTION"
                
                item = self.sprite_object.coa_anim_collections.add()
                item.name = "Restpose"
                item.frame_start = 0
                item.frame_end = 1
                
            item = self.sprite_object.coa_anim_collections.add()
            item.name = check_name(self.sprite_object.coa_anim_collections,"NewCollection")
            item.name_old = item.name
            item.action_collection = True
            
            self.sprite_object.coa_anim_collections_index = len(self.sprite_object.coa_anim_collections)-1
        else:
            return{'FINISHED'}    
    
    def create_actions(self,context):
        item = self.sprite_object.coa_anim_collections[self.sprite_object.coa_anim_collections_index]
        
        for child in get_children(context,self.sprite_object,ob_list=[]):
            if child.type == "ARMATURE":
                action_name = item.name + "_" + child.name
                
                action = None
                if action_name not in bpy.data.actions:
                    action = bpy.data.actions.new(action_name)
                else:
                    action = bpy.data.actions[action_name]
                action.use_fake_user = True    
                if child.animation_data == None:
                    child.animation_data_create()
                child.animation_data.action = action

    def execute(self, context):
        self.sprite_object = get_sprite_object(context.active_object)
        
        self.create_actions_collection(context)
        self.create_actions(context)
        
        
        return {"FINISHED"}
        
class RemoveAnimationCollection(bpy.types.Operator):
    bl_idname = "my_operator.remove_animation_collection"
    bl_label = "Remove Animation Collection"
    bl_description = ""
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True
    
    sprite_object = None
    
    def remove_actions_collection(self,context):
        if self.sprite_object != None:
            if self.sprite_object.coa_anim_collections[self.sprite_object.coa_anim_collections_index].name != "NO ACTION" and self.sprite_object.coa_anim_collections[self.sprite_object.coa_anim_collections_index].name != "Restpose":
                self.sprite_object.coa_anim_collections.remove(self.sprite_object.coa_anim_collections_index)
            if self.sprite_object.coa_anim_collections_index > 2:
                self.sprite_object.coa_anim_collections_index = self.sprite_object.coa_anim_collections_index - 1
            
            if len(self.sprite_object.coa_anim_collections) < 3:
                self.sprite_object.coa_anim_collections.remove(0)
                self.sprite_object.coa_anim_collections.remove(0)
            
    def remove_actions(self,context):
        item = self.sprite_object.coa_anim_collections[self.sprite_object.coa_anim_collections_index]
        
        for child in get_children(context,self.sprite_object,ob_list=[]):
            action_name = item.name + "_" + child.name
            
            if action_name in bpy.data.actions:
                if child.animation_data != None and child.animation_data.action == bpy.data.actions[action_name]:
                    child.animation_data_clear()
                bpy.data.actions[action_name].use_fake_user = False
                bpy.data.actions[action_name].user_clear()    
                bpy.data.actions.remove(bpy.data.actions[action_name])
        for area in context.screen.areas:
            if area.type == "DOPESHEETH_EDITOR":
                area.tag_redraw()
        context.scene.update()               
            
                    
    def execute(self, context):
        self.sprite_object = get_sprite_object(context.active_object)
        if len(self.sprite_object.coa_anim_collections) > 0:
            
            self.remove_actions(context)
            self.remove_actions_collection(context)
            
        return {"FINISHED"}
                
class CreateNlaTrack(bpy.types.Operator):
    bl_idname = "coa_operator.create_nla_track"
    bl_label = "Create NLA Track"
    bl_description = "Generate NLA Strips."
    bl_options = {"REGISTER","UNDO"}
    
    
    start = IntProperty(default=0)
    repeat = IntProperty(default=1)
    scale = FloatProperty(default=1.0)
    insert_at_cursor = BoolProperty(default=True)
    anim_collection_name = StringProperty()
    auto_blend = BoolProperty(default=True)
    extrapolation = EnumProperty(default="NOTHING",items=(("HOLD_FORWARD","Hold Forward","HOLD_FORWARD"),("HOLD","Hold","HOLD"),("NOTHING","Nothing","NOTHING")) )

    def check(self,context):
        return True
    
    @classmethod
    def poll(cls, context):
        return True

    def draw(self,context):
        layout = self.layout
        row = layout.row()
        row.prop(self,"insert_at_cursor",text="Insert Strip at Cursor Location")
        row = layout.row()
        row.prop(self,"auto_blend",text="Auto Blending")
        row = layout.row()
        if self.insert_at_cursor:
            row.active = False
            row.enabled = False
        row.prop(self,"start",text="Insert at Frame")
        row = layout.row()
        row.prop(self,"repeat",text="Repeat Strip")
        row = layout.row()
        row.prop(self,"scale",text="Scale Strip")
        row = layout.row()
        row.prop(self,"extrapolation",text="Strip Extrapolation")
        

    def invoke(self,context,event):
        wm = context.window_manager
        self.start = 0
        self.repeat = 1
        self.scale = 1.0
        #self.insert_at_cursor = True
        return wm.invoke_props_dialog(self)
    
    def get_empty_track(self,anim_data,strip_range):
        if len(anim_data.nla_tracks) == 0:
            return anim_data.nla_tracks.new()
        
        strip_space = range(strip_range[0],strip_range[1]+1)
        
        intersecting_strip_found = False
        for i,track in enumerate(anim_data.nla_tracks):
            track = anim_data.nla_tracks[i]
            if len(track.strips) == 0:
                return track
            
            
            for strip in track.strips:
                if (strip_range[0] > strip.frame_start and strip_range[0] < strip.frame_end) or (strip_range[1] > strip.frame_start and strip_range[1] < strip.frame_end):
                    intersecting_strip_found = True
                
        if not intersecting_strip_found:
            return track
               
        return anim_data.nla_tracks.new()
    
    def execute(self, context):
        obj = bpy.context.active_object
        sprite_object = get_sprite_object(obj)
        children = get_children(context,sprite_object,ob_list=[])
        
        context.scene.coa_nla_mode = "NLA"
        
        if self.anim_collection_name == "":
            anim_collection = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index]
        else:    
            anim_collection = sprite_object.coa_anim_collections[self.anim_collection_name]
        
        if self.insert_at_cursor:
            self.start = context.scene.frame_current
        
        for child in children:
            if child.animation_data != None:
                for track in child.animation_data.nla_tracks:
                    for strip in track.strips:
                        strip.select = False
                    
                action_name = anim_collection.name + "_" + child.name
                if action_name in bpy.data.actions:
                    action_start = 0
                    action_end = anim_collection.frame_end
                    strip_start = self.start
                    strip_end = self.start + anim_collection.frame_end
                    
                    
                    action = bpy.data.actions[action_name]
                    
                    if child.animation_data != None:
                        child.animation_data_create()
                        anim_data = child.animation_data
                        
                        nla_track = self.get_empty_track(anim_data,[strip_start,strip_end])  
                        strip = nla_track.strips.new(action_name,self.start,action)
                        strip.action_frame_start = action_start
                        strip.action_frame_end = action_end
                        
                        strip.frame_start = strip_start
                        strip.frame_end = strip_end
                        strip.repeat = self.repeat
                        strip.use_auto_blend = self.auto_blend
                        strip.scale = self.scale
                        strip.extrapolation = self.extrapolation
                    
                    
        return {"FINISHED"}
                        