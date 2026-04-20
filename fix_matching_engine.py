with open('/app/core/matching_engine/matching_engine.py', 'r') as f:
    content = f.read()

content = content.replace('''        if not self.weights.validate():
            raise ValueError("Invalid scoring weights")
            if not self.weights.validate():
            raise ValueError("Invalid scoring weights")''', '''        if not self.weights.validate():
            raise ValueError("Invalid scoring weights")''')

with open('/app/core/matching_engine/matching_engine.py', 'w') as f:
    f.write(content)
