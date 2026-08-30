from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Category, Product, StockTransaction


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['role_display'] = user.get_role_display()
        token['full_name'] = user.get_full_name() or user.username
        return token


    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'role_display': self.user.get_role_display(),
        }
        return data


class CustomUserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'role_display',
            'is_active',
            'date_joined',
            'last_login',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, default=CustomUser.Role.OPERARIO)
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password]
    )

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'password',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active',
        ]

    def validate_role(self, value):
        if value:
            val = str(value).lower()
            valid_roles = [CustomUser.Role.ADMIN, CustomUser.Role.BODEGUERO, CustomUser.Role.OPERARIO]
            if val not in valid_roles:
                raise serializers.ValidationError(f'Rol no válido. Opciones: {valid_roles}')
            return val
        return CustomUser.Role.OPERARIO

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(
        source='products.count',
        read_only=True
    )

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'description',
            'products_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'products_count', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'description',
            'price',
            'stock_actual',
            'category',
            'category_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'stock_actual', 'created_at', 'updated_at']

    def validate_sku(self, value):
        sku = value.strip().upper()
        instance = getattr(self, 'instance', None)
        if Product.objects.filter(sku__iexact=sku).exclude(pk=instance.pk if instance else None).exists():
            raise serializers.ValidationError('Ya existe un producto registrado con este SKU.')
        return sku


class StockTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    user_full_name = serializers.SerializerMethodField()
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    product_sku = serializers.CharField(
        source='product.sku',
        read_only=True
    )
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )

    class Meta:
        model = StockTransaction
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'transaction_type',
            'transaction_type_display',
            'quantity',
            'user',
            'user_username',
            'user_full_name',
            'notes',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'user_username',
            'user_full_name',
            'product_name',
            'product_sku',
            'transaction_type_display',
            'created_at'
        ]

    def get_user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def validate(self, attrs):
        product = attrs.get('product')
        transaction_type = attrs.get('transaction_type')
        quantity = attrs.get('quantity')

        if quantity is not None and quantity <= 0:
            raise serializers.ValidationError({
                'quantity': 'La cantidad debe ser un numero entero mayor a 0.'
            })

        if transaction_type == StockTransaction.TransactionType.SALIDA and product:
            if product.stock_actual < quantity:
                raise serializers.ValidationError({
                    'quantity': (
                        f'Stock insuficiente para "{product.name}". '
                        f'Stock actual disponible: {product.stock_actual}, solicitado: {quantity}.'
                    )
                })

        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)