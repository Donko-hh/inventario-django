from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Category, Product, StockTransaction


INPUT_CLASS = (
    "w-full px-4 py-2.5 rounded-lg border border-slate-300 "
    "bg-white text-slate-900 "
    "focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
)

SELECT_CLASS = (
    "w-full px-4 py-2.5 rounded-lg border border-slate-300 "
    "bg-white text-slate-900 "
    "focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm"
)

CHECKBOX_CLASS = "h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Nombre de usuario',
            'autofocus': True,
        }),
        label="Usuario",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Contrasena',
        }),
        label="Contrasena",
    )


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'category', 'price', 'description']
        widgets = {
            'sku': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej: LAP-001'}),
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombre descriptivo del producto'}),
            'category': forms.Select(attrs={'class': SELECT_CLASS}),
            'price': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '0.00', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3, 'placeholder': 'Especificaciones...'}),
        }

    def clean_sku(self):
        sku = self.cleaned_data['sku'].strip().upper()
        qs = Product.objects.filter(sku__iexact=sku)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un producto con este codigo SKU.')
        return sku


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej: Computacion'}),
            'description': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3, 'placeholder': 'Descripcion...'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        qs = Category.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe una categoria con este nombre.')
        return name


class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['product', 'transaction_type', 'quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_product_select'}),
            'transaction_type': forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_type_select'}),
            'quantity': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '1', 'min': '1'}),
            'notes': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2, 'placeholder': 'Motivo del movimiento...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        tx_type = cleaned_data.get('transaction_type')
        quantity = cleaned_data.get('quantity')

        if quantity is not None and quantity <= 0:
            self.add_error('quantity', 'La cantidad debe ser mayor a 0.')

        if product and tx_type == StockTransaction.TransactionType.SALIDA and quantity:
            if product.stock_actual < quantity:
                self.add_error(
                    'quantity',
                    f'Stock insuficiente para "{product.name}". '
                    f'Disponible: {product.stock_actual}, solicitado: {quantity}.'
                )

        return cleaned_data


class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        label="Contrasena",
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Contrasena segura'}),
        validators=[validate_password],
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'first_name', 'last_name', 'email', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombre de usuario'}),
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'correo@empresa.com'}),
            'role': forms.Select(attrs={'class': SELECT_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class CustomUserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Nueva Contrasena (opcional)",
        required=False,
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Dejar en blanco para mantener'}),
        validators=[validate_password],
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
            'role': forms.Select(attrs={'class': SELECT_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
        }