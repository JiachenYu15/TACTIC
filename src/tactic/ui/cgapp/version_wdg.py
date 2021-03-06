###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ['UnknownVersionContextWdg', 'CurrentVersionContextWdg','VersionWdg','SubRefWdg']

from pyasm.common import Xml, Container
from pyasm.search import Search
from pyasm.biz import Snapshot
from pyasm.web import *
from pyasm.widget import *
from pyasm.prod.biz import SessionContents
from tactic.ui.common import BaseTableElementWdg


class UnknownVersionContextWdg(BaseTableElementWdg):
    
    def init(self):
        self.has_data = False
        self.is_loaded = None

    def get_status(self):
        return VersionWdg.NOT_CURRENT

    def get_display(self):
       
        version = self.get_option('version')
        display = 'v%0.3d' %version
        
        status = self.get_status()
        widget = VersionWdg.get(status)
        widget.add(display)
        
        return widget


class CurrentVersionContextWdg(BaseTableElementWdg):
    
    def init(self):
        self.has_data = False
        self.is_loaded = None

    def get_data(self):
        self.is_loaded = True
        self.session_version = self.get_option('session_version')
        self.current_version =  self.get_option('current_version')
        self.session_context = self.get_option('session_context')
        self.current_context = self.get_option('current_context')
        self.session_revision = self.get_option('session_revision')
        self.current_revision =  self.get_option('current_revision')

        if not self.current_version:
            self.current_version = 0
        
        if self.session_version in ['', None]:
            self.session_version = 0
            self.is_loaded = False
                
        if not self.session_revision:
            self.session_revision = 0
        else:
            self.session_revision = int(self.session_revision)
        if not self.current_revision:
            self.current_revision = 0
        else:
            self.current_revision = int(self.current_revision)
        self.has_data = True
  
    def get_status(self):
        if not self.has_data:
            self.get_data()
        '''
        is_loaded = False
        if self.session_version:
            is_loaded = True
        '''
        is_loaded = self.is_loaded
        if is_loaded:    
            if self.session_context != self.current_context:
                return VersionWdg.MISMATCHED_CONTEXT
            elif self.session_version == self.current_version:
                if self.session_revision == self.current_revision:
                    return VersionWdg.UPDATED 
                elif self.session_revision < self.current_revision:
                    return VersionWdg.OUTDATED
                else:
                    return VersionWdg.NOT_CURRENT

            elif self.session_version < self.current_version:
                return VersionWdg.OUTDATED
            else: # session has a version not found in db
                return VersionWdg.NOT_CURRENT
        else:
             return VersionWdg.NOT_LOADED

    def get_display(self):
        
        self.get_data()
        display = "v%0.3d" % int(self.current_version)
        if self.current_revision:
            display = "%s r%0.3d" % (display, int(self.current_revision))
        
        status = self.get_status()
        widget = VersionWdg.get(status)
        widget.add(display)
        
        return widget

class VersionWdg(Widget):
    '''Widget that displays the status/currency of a loaded object in the UI'''
    MISMATCHED_CONTEXT, UPDATED, OUTDATED, NOT_CURRENT, NOT_LOADED = xrange(5)
    def get(cls, status):
        widget = Widget()
        if status == cls.MISMATCHED_CONTEXT:
            widget.add(IconWdg(icon=IconWdg.DOT_GREY))
            widget.add("*")
        elif status == cls.UPDATED:
            widget.add(IconWdg(icon=IconWdg.DOT_GREEN))
        elif status == cls.NOT_CURRENT:
            widget.add(IconWdg(name='not current', icon=IconWdg.DOT_YELLOW))
        elif status == cls.OUTDATED:
            widget.add(IconWdg(name='outdated', icon=IconWdg.DOT_RED))
        elif status == cls.NOT_LOADED:
            widget.add(IconWdg(icon=IconWdg.DOT_GREY))
        else:
            widget.add(IconWdg(icon=IconWdg.DOT_GREY))

        return widget

    get = classmethod(get)

class SubRefWdg(AjaxWdg):
    '''Widget that draws the hierarchical references of the asset of interest'''
    CB_NAME = "load_snapshot"

    def init(self):
        self.version_wdgs = []

    def set_info(self, snapshot, session, namespace):
        self.session = session
        self.snapshot = snapshot
        self.namespace = namespace

        # handle ajax settings
        self.widget = DivWdg()
        self.set_ajax_top(self.widget)
        self.set_ajax_option("namespace", self.namespace)
        self.set_ajax_option("snapshot_code", self.snapshot.get_code())

    def init_cgi(self):
        web = WebContainer.get_web()
        snapshot_code = web.get_form_value("snapshot_code")
        namespace = web.get_form_value("namespace")

        snapshot = Snapshot.get_by_code(snapshot_code)
        session = SessionContents.get(asset_mode=True)

        self.set_info(snapshot, session, namespace)

    def get_version_wdgs(self):
        '''get a list of version wdgs'''
        if self.version_wdgs:
            return self.version_wdgs
        xml = self.snapshot.get_xml_value("snapshot")
        refs = xml.get_nodes("snapshot/file/ref")
        if not refs:
            return self.version_wdgs

       
        # handle subreferences
        for ref in refs:

            instance = Xml.get_attribute(ref, "instance")
            node_name = Xml.get_attribute(ref, "node_name")
            snapshot = Snapshot.get_ref_snapshot_by_node(ref, mode='current')
            if not snapshot:
                print "WARNING: reference in snapshot [%s] does not exist" % self.snapshot.get_code()
                wdg = UnknownVersionContextWdg()
                context = Xml.get_attribute(ref, "context")
                version = Xml.get_attribute(ref, "version")
                try:
                    version = int(version)
                except ValueError:
                    versionm = 0
                data = {'node_name': node_name, 'context': context, 
                        'version': version}
                wdg.set_options(data)

                self.version_wdgs.append(wdg)
                continue

            #checkin_snapshot = Snapshot.get_ref_snapshot_by_node(ref)

            parent = snapshot.get_parent()
                
            asset_code = parent.get_code()

            # namespace = "veryron_rig"
            # node_name = "stool_model:furn001"
            # instance =  "stool_model"
            
            # HACK: if node name was not specified, then try to guess it
            # (for backwards compatibility)
            if not node_name: 
                node_name = self.get_node_name(snapshot, asset_code, self.namespace)
                # HACK
                parts = node_name.split(":")
                parts.insert(1, instance)
                node_name = ":".join(parts)
                print "WARNING: node_name not given: using [%s]" % node_name


            # Add the current namespace to the node 
            # in session
            checked_node_name = node_name

            # FIXME: this is Maya-specific and meant for referencing a shot
            '''
            if app_name == 'Maya':
                
                if not node_name.startswith("%s:" % self.namespace):
                    node_name = "%s:%s" % (self.namespace, node_name)
            elif app_name == "XSI":
                pass
            ''' 
            # get the current information
            current_version = snapshot.get_value("version")
            current_context = snapshot.get_value("context")
            current_revision = snapshot.get_value("revision", no_exception=True)
            current_snapshot_type = snapshot.get_value("snapshot_type")


            # get the session information
            self.session.set_asset_mode(False)
            session_context = self.session.get_context(node_name, asset_code, current_snapshot_type)
            session_version = self.session.get_version(node_name, asset_code, current_snapshot_type)
            session_revision = self.session.get_revision(node_name, asset_code, current_snapshot_type)
            #print "session: ", session_version, session_context, session_revision
            # add to outdated ref list here, this is really current even though it's called current

            version_wdg = CurrentVersionContextWdg()
            data = {'session_version': session_version, \
                'session_context': session_context,  \
                'session_revision': session_revision,  \
                'current_context': current_context, \
                'current_version': current_version, \
                'current_revision': current_revision,\
                'asset_code': asset_code,\
                'node_name': checked_node_name ,\
                'sobject': parent,\
                'snapshot': snapshot}

            version_wdg.set_options(data)
            self.version_wdgs.append(version_wdg)

            # This only adds when it is being drawn with the corresponding process selected
            # so not that useful, commented out for now.
            #if version_wdg.get_status() not in [ VersionWdg.NOT_LOADED, VersionWdg.UPDATED]:
            #    SubRefWdg.add_outdated_ref(version_wdg)

        return self.version_wdgs

    def get_display(self):

        assert self.snapshot
        assert self.session
        assert self.namespace

        widget = self.widget
        

        if not self.is_ajax():
            return widget
 
        #widget.add_style("border-style: solid")
        #widget.add_style("padding: 10px")
        #widget.add_style("position: absolute")
        #widget.add_style("margin-left: 50px")
        widget.add_style("text-align: left")
        table = Table()
        
        version_wdgs = self.get_version_wdgs()

        for version_wdg in version_wdgs:
            # draw the info
            tr = table.add_row()
            #checkbox = CheckboxWdg(self.CB_NAME)
            #checkbox.set_option("value", "cow" )
            #table.add_cell( checkbox )

            td = table.add_cell(version_wdg)
            td.set_attr("nowrap", "1")
            current_context = version_wdg.get_option('current_context')
            if current_context:
                table.add_cell(HtmlElement.b("(%s)" % current_context))
            else:
                checkin_context = version_wdg.get_option('context')
                td = table.add_cell("(%s)" % checkin_context)
                tr.add_style('background-color: #7D0000')
                
            table.add_cell(version_wdg.get_option('asset_code'))
            node_name = version_wdg.get_option('node_name')
            if node_name:
                table.add_cell(node_name.split(":")[0])

        widget.add("<hr size='1'>")
        widget.add("References")
        widget.add(table)

        return widget


    def get_overall_status(self):
        version_wdgs = self.get_version_wdgs()
        all_updated = True
        is_loaded = False
        for wdg in version_wdgs:
            status = wdg.get_status()
            if status != VersionWdg.NOT_LOADED:
                is_loaded = True
            if wdg.get_status() != VersionWdg.UPDATED:
                all_updated = False
                # don't use break as we need the info of all the subrefs
                continue
                
        
        if not is_loaded:
            return VersionWdg.NOT_LOADED
        elif all_updated == False:
            return VersionWdg.OUTDATED
        else: 
            return VersionWdg.UPDATED

    def get_node_name(self, snapshot, asset_code, namespace):
        ''' if possible get the node name from snapshot which is more accurate'''
        node_name = snapshot.get_node_name()

        if not node_name:
            naming = MayaNodeNaming()
            app_name = WebContainer.get_web().get_selected_app() 
            if app_name == "Maya":
                naming = MayaNodeNaming()
            elif app_name == "XSI":
                naming = XSINodeNaming()
            elif app_name == "Houdini":
                naming = HoudiniNodeNaming()
            naming.set_asset_code(asset_code)
            naming.set_namespace(namespace)

            node_name = naming.build_node_name()
        return node_name

    def add_outdated_ref(version_wdg):
        Container.append_seq('SubRef_outdated', version_wdg)
    add_outdated_ref = staticmethod(add_outdated_ref)

    def get_outdated_ref():
        return Container.get('SubRef_outdated')
    get_outdated_ref = staticmethod(get_outdated_ref)

