def try_consume(consumer, stream, ast):
    result, data = consumer(stream)
    if result:
        ast.append(data)
        return True

    return False


char_stream = []
consumers = []
ast = []
while char_stream.peak() != None:
    for consumer in consumers:
        if try_consume(consumer, char_stream, ast):
            break
