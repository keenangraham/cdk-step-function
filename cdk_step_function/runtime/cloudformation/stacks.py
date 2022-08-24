def get_stacks_to_delete(event, context):
    print(event)
    return [
        'stackA',
        'stackB',
        'stackC',
    ]
