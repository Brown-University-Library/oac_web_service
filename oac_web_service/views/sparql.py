import traceback
from flask import request, jsonify, make_response
from oac_web_service import app
from oac_web_service.models.annotation import Annotation, AnnotationError
from java.lang import String, NullPointerException
from com.hp.hpl.jena.tdb import TDBFactory
from com.hp.hpl.jena.query import QueryParseException, QueryFactory, QueryExecutionFactory, ResultSetFormatter, ReadWrite

@app.route('/sparql', methods=['POST','GET'])
def sparql():
    """
        A POST or GET method to query the Open Annotations index with a SPARQL Query

        This method has READ access to the Annotations index.

        Required parameters:

          query:      The SPARQL query to execute

    """
    sparql_xml_results = ""
    try:
        if request.method == 'POST':
            q = request.form.get('query', None)
        else:
            q = request.args.get('query', None)

        query = QueryFactory.create(String(q))

        # Start dataset READ transaction
        dataset = TDBFactory.createDataset(app.config['STORE_LOCATION'])
        dataset.begin(ReadWrite.READ)
        try:
            qexec = QueryExecutionFactory.create(query, dataset)
            results = qexec.execSelect()
            try:
                sparql_xml_results = ResultSetFormatter.asXMLString(results)
            finally:
                qexec.close()
        finally:
            dataset.end()

    except AnnotationError, ex:
        return jsonify({'value' : ex.value, 'trace' : traceback.format_stack()})
    except QueryParseException, ex:
        return jsonify({'error' : "SPARQL query not parsable."})
    except NullPointerException, ex:
        return jsonify({'error' : "No SPARQL query found.  Please POST a valid SPARQL query in the 'query' parameter of the request"})
    except Exception, ex:
        raise
    else:
        resp = make_response(unicode(sparql_xml_results))
        resp.mimetype = 'text/xml'
        return resp