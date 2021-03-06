from oac_web_service.models.foxml import Foxml
from oac_web_service.models.fedora import Fedora
from oac_web_service import app
from rdflib.graph import Graph, plugin
from rdflib.serializer import Serializer
from xml.etree import ElementTree as ET

plugin.register("rdf-json", Serializer, "rdflib_jsonld.jsonld_serializer", "JsonLDSerializer")

class Annotation(object):
    def __init__(self, **kwargs):
        self._errors = []

        self._annotation_pid = kwargs.pop('annotation_pid', None)

        # Required fields
        self._source_uri = kwargs.pop('source_uri', None)
        self._dc_title = kwargs.pop('dc_title', None)

        # Either an inline, URI, or a content/mimetype pair must be present
        self._body_uri = kwargs.pop('body_uri', None)
        self._body_content = kwargs.pop('body_content', None)
        self._body_mimetype = kwargs.pop('body_mimetype', None)
        self._body_content_model = kwargs.pop('body_content_model', None)
        self._body_inline = kwargs.pop('body_inline', None)
        
        # Optional fields
        self._annotated = kwargs.pop('annotated', None)
        self._annotator = kwargs.pop('annotator', None)
        self._generator = kwargs.pop('generator', None)
        self._oax_style_uri = kwargs.pop('oax_style_uri', None)
        self._oa_selector = kwargs.pop('oa_selector', None)
        self._oa_selector_type_uri = kwargs.pop('oa_selector_type_uri', None)
        self._fragment_type = kwargs.pop('fragment_type', None)

    def create(self):
        if self._source_uri is None or self._dc_title is None:
            raise AnnotationError("source_uri and dc_title are required for Creating")

        self._body = None
        self._annotation = None
        self.build_body() 
        self.build_annotation()

    @classmethod
    def serialize(cls, pids, format=None, check_object=None):
        """
        Get list of datastreams from an array of PIDs

        With those, get all rdf:Description elements and output
        in the format specified.

        Format options are:
            - rdf/xml or xml (default)
            - rdf/json or json
            - turtle or ttl
            - nt
            - n3

        Optional "check_object" parameter will check the object's
        content model before serializing to make sure it is equal to the
        default content type for annotate objects set in the config.
        """
        if format is None:
            format = 'xml'

        if check_object is None:
            check_object = True

        xmls = []

        for pid in pids:

            # Make sure we only serialize Annotation objects
            if check_object:
                try:
                    content_models = Fedora.get_content_models(pid)
                except:
                    raise AnnotationError("PID %s not found in Fedora" % pid)
                    
                oac_model = "info:fedora/%s" % app.config.get('DEFUALT_ANNOTATION_CONTENT_MODEL')
                if oac_model not in content_models:
                    continue

            datastreams = Fedora.get_datastream_list(pid)
            if not isinstance(datastreams, list):
                # There was an error with this PID, skip it
                continue
            for d in datastreams:
                [xmls.append(x) for x in Foxml.get_rdf_descriptions(Fedora.get_datastream(pid, d))]

        rdf_xml_string = Foxml.get_rdf_string_from_descriptions(list(xmls))

        out = Graph()
        out.parse(data=rdf_xml_string, format="application/rdf+xml")

        if format.lower() == 'rdf/xml' or format.lower() == 'xml':
            return out.serialize(format="xml"), "application/rdf+xml"
        if format.lower() == 'n3':
            return out.serialize(format="n3"), "text/rdf+n3"
        elif format.lower() == 'turtle' or format.lower() == 'ttl':
            return out.serialize(format="turtle"), "text/turtle"
        elif format.lower() == 'nt':
            return out.serialize(format="nt"), "text/nt"
        elif format.lower() == 'rdf/json' or format.lower() == 'json':
            return out.serialize(format="rdf-json"), "application/rdf+json"
        else:
            raise AnnotationError("Serialization format '%s' is not supported.")


    def load(self):
        """
        Get an annotation object from Fedora (by PID) and load it locally as an
        Annotation object.
        """        

    def edit(self):
        if self._annotation_pid is None:
            raise AnnotationError("pid is required for Editing")

        # Dublin Core Datastream
        if self._dc_title is not None:
            dc_annotation = "DC"
            dublin_core = Foxml.get_dublin_core_element(pid=self._annotation_pid, title=self._dc_title)
            Fedora.put_datastream(pid=self._annotation_pid, dsid=dc_annotation, element=dubln_core)

    def build_body(self):
        if self._body_uri is None and self._body_inline is None:
            try:
                assert self._body_content is not None
                assert self._body_mimetype is not None

                self._body_pid = Fedora.get_pid()

                foxml = Foxml(pid=self._body_pid)
                # Object Properties
                foxml.create_object_properties()
                # Dublin Core Datastream
                dublin_core = Foxml.get_dublin_core_element(pid=self._body_pid, title="Open Annotation Collaboration body object (B-1)")
                foxml.create_xml_datastream(element=dublin_core,
                                            id="DC",
                                            version_id="DC1",
                                            mime="text/xml",
                                            label="Dublin Core Record for this object")
                # Attach body
                if self._body_mimetype == "text/xml":
                    foxml.create_xml_datastream(element=self._body_content,
                                                id="OAC_BODY",
                                                label="OAC Body Content",
                                                mime=self._body_mimetype)
                else:
                    raise AnnotationError("Only body contents with mimetype 'text/xml' is allowed at this time.")

                # Optional RELS-EXT Datastream for the content model
                if self._body_content_model is not None:
                    body_rels_ext_rdf_element = Foxml.get_rels_ext_model_element(pid=self._body_pid,
                                                                                 models=[self._body_content_model])
                    foxml.create_xml_datastream(element=body_rels_ext_rdf_element,
                                                id="RELS-EXT",
                                                mime="application/rdf+xml",
                                                label="RDF Statements about this object",
                                                format_uri="info:fedora/fedora-system:FedoraRELSExt-1.0")
                    
                self._body_uri = "info:fedora/%s" % self._body_pid
                self._body = foxml.get_foxml()
            except:
                raise# AnnotationError("Could not create the (B-1) body object from passed parameters")

    def build_annotation(self):
        self._annotation_pid = Fedora.get_pid()

        foxml = Foxml(pid=self._annotation_pid)
        self._annotation_uri = "info:fedora/%s" % self._annotation_pid

        # Object Properties
        foxml.create_object_properties()
        # Dublin Core Datastream
        dc_uri = "%s/DC" % self._annotation_uri
        dublin_core = Foxml.get_dublin_core_element(pid=self._annotation_pid, title=self._dc_title)
        foxml.create_xml_datastream(element=dublin_core,
                                    id="DC",
                                    version_id="DC1",
                                    mime="text/xml",
                                    label="Dublin Core Record for this object",
                                    fedora_uri=dc_uri,
                                    format_uri="http://www.openarchives.org/OAI/2.0/oai_dc/")


        # Inline Body Datastream
        self.body_inline_rdf_element = None
        if self._body_inline is not None:
            self._body_uri = "%s/inlinebody" % self._annotation_uri
            self.body_inline_rdf_element = Foxml.get_body_inline_rdf_element(pid=self._annotation_pid,
                                                                     body_uri=self._body_uri,
                                                                     body_inline=self._body_inline)
            foxml.create_xml_datastream(element=self.body_inline_rdf_element,
                                        id="inlinebody",
                                        mime="application/rdf+xml",
                                        label="Inline Body for OAC annotation",
                                        fedora_uri=self._body_uri)

        # Annotation Datastream
        anno_uri = "%s/annotation" % self._annotation_uri
        self.annotation_rdf = Foxml.get_annotation_rdf_element(pid=self._annotation_pid,
                                                               body_uri=self._body_uri,
                                                               oa_selector=self._oa_selector,
                                                               body_mimetype=self._body_mimetype,
                                                               annotated=self._annotated,
                                                               generator=self._generator,
                                                               annotator=self._annotator)
        foxml.create_xml_datastream(element=self.annotation_rdf,
                                    id="annotation",
                                    mime="application/rdf+xml",
                                    label="OAC annotation core",
                                    fedora_uri=anno_uri)

        # RELS-EXT Datastream
        # This 'get' should never fall back to '' because there is a default annotation content model ('oac:oa-annotation')
        oac_model = app.config.get('DEFUALT_ANNOTATION_CONTENT_MODEL', '')

        # The PID of the SDef object for Annotation Serialization
        # This is not required by Fedora so it was removed.
        # serialization_service = "oac-sdef:serialize"
        #self.rels_ext_rdf_element = Foxml.get_rels_ext_model_element(pid=self._annotation_pid,
        #                                                             models=[oac_model],
        #                                                             services=[serialization_service])
        self.rels_ext_rdf_element = Foxml.get_rels_ext_model_element(pid=self._annotation_pid,
                                                                     models=[oac_model])
        foxml.create_xml_datastream(element=self.rels_ext_rdf_element,
                                    id="RELS-EXT",
                                    mime="application/rdf+xml",
                                    label="RDF Statements about this object",
                                    format_uri="info:fedora/fedora-system:FedoraRELSExt-1.0")

        self.specific_target_rdf_element = None
        self.selector_rdf_element = None
        if self._oa_selector is not None:
            # SpecificTarget Datastream
            sptg_uri = "%s/specifictarget" % self._annotation_uri
            self.specific_target_rdf_element = Foxml.get_specific_target_rdf_element(pid=self._annotation_pid,
                                                                                     source_uri=self._source_uri,
                                                                                     oax_style_uri=self._oax_style_uri)
            foxml.create_xml_datastream(element=self.specific_target_rdf_element,
                                        id="specifictarget",
                                        mime="application/rdf+xml",
                                        label="SpecificTarget data for OAC annotation",
                                        fedora_uri=sptg_uri)

            # Selector Datastream
            sele_uri = "%s/selector" % self._annotation_uri
            self.selector_rdf_element = Foxml.get_selector_rdf_element(pid=self._annotation_pid,
                                                                       oa_selector=self._oa_selector,
                                                                       oa_selector_type_uri=self._oa_selector_type_uri,
                                                                       fragment_type=self._fragment_type)
            foxml.create_xml_datastream(element=self.selector_rdf_element,
                                        id="selector",
                                        mime="application/rdf+xml",
                                        label="Selector data for OAC annotation",
                                        fedora_uri=sele_uri)

        self._annotation = foxml.get_foxml()

    def validate(self):
        """
            Validate that the body and annotation objects
            were created in Fedora correctly
        """
        if not len(self._errors) == 0:
            raise AnnotationError(" ".join(self._errors))
        else:
            return True

    def submit(self):
        """
            Send body and annotate objects to Fedora
        """
        if self._body:
            self._body_response = Fedora.post_foxml(element=self._body)

        if self._annotation:
            self._annotation_response = Fedora.post_foxml(element=self._annotation)

    def get_results(self):
        return  {
                    'errors'            : self._errors,
                    'body_uri'          : self._body_uri,
                    'annotation_uri'    : self._annotation_uri
                }
    results = property(get_results, None)

class AnnotationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)